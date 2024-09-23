from zep_python import ZepClient, MemorySearchPayload
from zep_python.memory import Memory, Message
import asyncpg
import uuid
import numpy as np
from datetime import datetime, timedelta
import openai
from config import *

class ZepIntegration:
    

    async def get_session_id(self, chat_id: str) -> str:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                'SELECT session_id FROM sessions WHERE chat_id = $1',
                chat_id
            )
            if row:
                return str(row['session_id'])
            session_id = str(uuid.uuid4())
            await conn.execute(
                'INSERT INTO sessions (chat_id, session_id) VALUES ($1, $2)',
                chat_id, session_id
            )
            return session_id

    async def add_memory(self, chat_id: str, role: str, content: str, timestamp=None):
        session_id = await self.get_session_id(chat_id)
        memory = Memory(
            messages=[Message(role=role, content=content, timestamp=timestamp or datetime.utcnow())],
            metadata={"session_id": session_id}
        )
        await self.zep_client.memory.aadd_memory(session_id, memory)

    async def get_chat_history(self, chat_id: str):
        session_id = await self.get_session_id(chat_id)
        return await self.zep_client.message.aget_session_messages(session_id)

    async def search_memory(self, chat_id: str, query: str, limit: int = 5):
        session_id = await self.get_session_id(chat_id)
        search_payload = MemorySearchPayload(
            text=query,
            search_scope="messages",
            search_type="mmr",
            mmr_lambda=MMR_LAMBDA
        )
        return await self.zep_client.memory.asearch_memory(session_id, search_payload, limit=limit)

    async def create_summary(self, chat_id: str, messages: list):
        session_id = await self.get_session_id(chat_id)
        combined_text = "\n".join([f"{msg.role}: {msg.content}" for msg in messages])
        summary_prompt = f"Summarize the following conversation in {SUMMARY_WORD_LIMIT} words or less. "
        summary_prompt += f"Style: {SUMMARY_STYLE}. Focus: {SUMMARY_FOCUS}. "
        if SUMMARY_SENTIMENT:
            summary_prompt += "Include overall sentiment. "
        if SUMMARY_ENTITIES:
            summary_prompt += "Highlight key entities or names. "
        summary_prompt += "Conversation:\n" + combined_text

        response = await openai.ChatCompletion.acreate(
            model=SUMMARIZATION_MODEL,
            messages=[
                {"role": "system", "content": "You are a summarization assistant."},
                {"role": "user", "content": summary_prompt}
            ]
        )
        summary = response.choices[0].message['content']

        summary_memory = Memory(
            messages=[Message(role="system", content=f"Summary: {summary}")],
            metadata={"type": "summary", "start_time": messages[0].created_at, "end_time": messages[-1].created_at}
        )
        await self.zep_client.memory.aadd_memory(session_id, summary_memory)

    async def get_relevant_context(self, chat_id: str, query: str, max_tokens: int):
        session_id = await self.get_session_id(chat_id)
        
        

        # Get graph context
        graph_context = await self.get_graph_context(query, graph_token_limit)

        # Get Zep facts context
        facts_context = await self.get_facts_context(session_id, query, facts_token_limit)

        # Get message and summary context
        searchPayload = MemorySearchPayload(
            text=query,
            search_scope="summary"
        )
        results = await self.zep_client.memory.asearch_memory(session_id, searchPayload, limit=SEARCH_RESULT_LIMIT)

        summaries = [r for r in results if r.metadata.get('type') == 'summary']
        messages = [r for r in results if r.metadata.get('type') != 'summary']

        query_embedding = await self.zep_client.memory.acreate_embedding(query)
        summary_embeddings = [await self.zep_client.memory.acreate_embedding(s.content) for s in summaries]
        message_embeddings = [await self.zep_client.memory.acreate_embedding(m.content) for m in messages]

        ranked_summaries = self.rank_by_relevance(query_embedding, summary_embeddings, summaries)
        ranked_messages = self.rank_by_relevance(query_embedding, message_embeddings, messages)

        summary_context = self.select_context(ranked_summaries, summary_token_limit)
        message_context = self.select_context(ranked_messages, message_token_limit)

        # Combine all context types
        combined_context = self.merge_context(graph_context, facts_context, summary_context, message_context)

        return combined_context

    async def get_graph_context(self, query: str, max_tokens: int):
        # Identify entities in the query
        entities = await self.zep_client.graph.identify_entities(query)
        entities = entities[:MAX_GRAPH_ENTITIES]  # Limit the number of entities

        graph_context = []
        current_tokens = 0

        for entity in entities:
            # Get entity information
            entity_info = await self.zep_client.graph.get_entity_info(entity)
            entity_text = f"Entity: {entity}\nInfo: {entity_info}\n"
            
            # Get related entities
            related_entities = await self.zep_client.graph.get_related_entities(entity, depth=GRAPH_RELATION_DEPTH)
            related_text = "Related: " + ", ".join(related_entities) + "\n"

            combined_text = entity_text + related_text
            if current_tokens + self.count_tokens(combined_text) <= max_tokens:
                graph_context.append(combined_text)
                current_tokens += self.count_tokens(combined_text)
            else:
                break

        return "\n".join(graph_context)

    async def get_facts_context(self, session_id: str, query: str, max_tokens: int):
        facts = await self.zep_client.memory.get_facts(session_id)
        
        # Filter facts based on confidence threshold
        confident_facts = [f for f in facts if f.confidence >= FACTS_CONFIDENCE_THRESHOLD]
        
        # Sort facts by relevance to the query
        query_embedding = await self.zep_client.memory.acreate_embedding(query)
        fact_embeddings = [await self.zep_client.memory.acreate_embedding(f.fact) for f in confident_facts]
        ranked_facts = self.rank_by_relevance(query_embedding, fact_embeddings, confident_facts)
        
        facts_context = []
        current_tokens = 0
        
        for fact, relevance in ranked_facts[:MAX_FACTS]:
            fact_text = f"Fact: {fact.fact} (Confidence: {fact.confidence:.2f})"
            if current_tokens + self.count_tokens(fact_text) <= max_tokens:
                facts_context.append(fact_text)
                current_tokens += self.count_tokens(fact_text)
            else:
                break
        
        return "\n".join(facts_context)

    def select_context(self, ranked_items, max_tokens):
        selected = []
        current_tokens = 0

        for item, relevance in ranked_items:
            if relevance < RELEVANCE_THRESHOLD:
                break
            item_tokens = self.count_tokens(item.content)
            if current_tokens + item_tokens <= max_tokens:
                selected.append(item.content)
                current_tokens += item_tokens
            else:
                break

        return "\n".join(selected)

    def merge_context(self, graph_context, facts_context, summary_context, message_context):
        return f"Graph Context:\n{graph_context}\n\nFacts:\n{facts_context}\n\nSummary Context:\n{summary_context}\n\nMessage Context:\n{message_context}"

    @staticmethod
    def rank_by_relevance(query_embedding, candidate_embeddings, candidates):
        similarities = [ZepIntegration.cosine_similarity(query_embedding, emb) for emb in candidate_embeddings]
        ranked = sorted(zip(candidates, similarities), key=lambda x: x[1], reverse=True)
        return ranked

    @staticmethod
    def cosine_similarity(v1, v2):
        if VECTOR_NORMALIZATION:
            v1 = v1 / np.linalg.norm(v1)
            v2 = v2 / np.linalg.norm(v2)
        return np.dot(v1, v2)

    @staticmethod
    def count_tokens(text):
        # This is a simplified token counting method. In a real implementation,
        # you might want to use a tokenizer that matches your model's tokenization.
        return len(text.split())

