import datetime
from collections import defaultdict

from multibot import Platform

AUDIT_LOG_AGE = datetime.timedelta(hours=1)
AUDIT_LOG_LIMIT = 5
AUTO_WEATHER_EVERY = datetime.timedelta(hours=6)
CHECK_PUNISHMENTS_EVERY_SECONDS = datetime.timedelta(hours=1).total_seconds()
CONNECT_4_AI_DELAY_SECONDS = 1
CONNECT_4_CENTER_COLUMN_POINTS = 2
CONNECT_4_N_COLUMNS = 7
CONNECT_4_N_ROWS = 6
FLOOD_2s_LIMIT = 2
FLOOD_7s_LIMIT = 4
HEAT_PERIOD_SECONDS = datetime.timedelta(minutes=15).total_seconds()
HELP_MINUTES_LIMIT = 1
INSTAGRAM_BAN_SLEEP = datetime.timedelta(days=1)
INSULT_PROBABILITY = 0.00166666667
MAX_PLACE_QUERY_LENGTH = 50
PUNISHMENT_INCREMENT_EXPONENT = 6
PUNISHMENTS_RESET_TIME = datetime.timedelta(weeks=2)
RECOVERY_DELETED_MESSAGE_BEFORE = datetime.timedelta(hours=1)
SCRAPING_TIMEOUT_SECONDS = 10

BANNED_POLL_PHRASES = (
 "Stop fucking around {presser_name} because you can't vote here",
 "It's not a shame {presser_name}, you're not allowed to vote here",
 "Stop pressing buttons you can't vote here {presser_name}",
 "{presser_name} stop trying to vote here because you can't",
 "You have been banned from voting here {presser_name}.",
 "You can't vote here, {presser_name}."
)

BYE_PHRASES = ('Goodbye.', 'goodbye', 'byyeeee', 'bye', 'see you again',
 'see you later', 'see you never', 'see you soon', 'see you next time', 'see you', 'see you later')

CHANGEABLE_ROLES = defaultdict(
    lambda: defaultdict(list),
    {
        Platform.DISCORD: defaultdict(
            list,
            {
                360868977754505217: [881238165476741161, 991454395663401072, 1033098591725699222, 1176639571677696173],
                862823584670285835: [976660580939202610, 984269640752590868]
            }
        )
    }
)

DISCORD_HEAT_NAMES = [
'Fresh Channel',
 'Hot Channel',
 'Caloret Channel',
 'Red Hot Channel',
 'Burning Canal',
 'HELL Channel'
]

DISCORD_HOT_CHANNEL_IDS = {
    'A': 493529846027386900,
    'B': 493529881125060618,
    'C': 493530483045564417,
    'D': 829032476949217302,
    'E': 829032505645596742
}

HELLO_PHRASES = ('hello', 'hi','how are you','nice to meet you', 'hey',' dear')

INSULTS = ('._.', 'aha', 'Stay away from me.', 'When in doubt my middle finger greets you.', "I'll ban you soon.",
 'Shut up noob.', 'Tiring.', 'Tell me less.', 'Tell me more.', 'Shut up now.', 'Shut up.',
 'You give a damn.', 'Really. You are about to be locked up.', 'They should do the C4 tactics.',
 'Say goodbye to your account.', 'Leave me alone.', 'Enjoy cancer brain.', "You're short, huh?", 'You are meaner than hitting a father.', 'You are dumber than combing light bulbs.',
 "You're dumber than pinching glass.", "You're sick from the roof.", "You're sick in the head.",
 'Flanagan is prettier than you.', 'You talk so much shit that your ass is envious of your mouth.',
 'There is a host contest and you have all the ballots.', 'Crazy.', "Dumfer and you won't be born.",
 "You're not very smart...", 'Heavy.', "That's good, eh?", 'Leave me alone.', 'How annoying.',
 'Remove the bug.', 'Report my weapon.', 'Reported.', 'Retard.', "I'm going to break your balls.",
 "You... you're not very well, are you?", "We're here again...", "We're here...", 'enjoy xd', "Why don't you shut up?", 'Who asked you?', 'What do you want?', "Will you shut up or I'll shut you up?",
 "Do you imagine I'm interested?", 'Will you shut up?', 'Is everything okay?',
 'Are you like that or do you get brain blackouts?','🖕', '😑', '🙄', '🤔', '🤨')

KEYWORDS = {
    'choose': ('choose', 'elige', 'escoge'),
    'connect_4': (('conecta', 'connect', 'ralla', 'raya'), ('4', 'cuatro', 'four')),
    'covid_chart': ('case', 'caso', 'contagiado', 'contagio', 'corona', 'coronavirus', 'covid', 'covid19', 'death',
                    'disease', 'enfermedad', 'enfermos', 'fallecido', 'incidencia', 'jacovid', 'mascarilla', 'muerte',
                    'muerto', 'pandemia', 'sick', 'virus'),
    'currency_chart': ('argentina', 'bitcoin', 'cardano', 'cripto', 'crypto', 'criptodivisa', 'cryptodivisa',
                       'cryptomoneda', 'cryptocurrency', 'currency', 'dinero', 'divisa', 'ethereum', 'inversion',
                       'moneda', 'pasta'),
    'dice': ('dado', 'dice'),
    'force': ('force', 'forzar', 'fuerza'),
    'multiple_answer': ('multi', 'multi-answer', 'multiple', 'multirespuesta'),
    'poll': ('encuesta', 'quiz', 'votacion', 'votar', 'voting'),
    'punish': ('acaba', 'aprende', 'ataca', 'atalo', 'azota', 'beating', 'boss', 'castiga', 'castigo', 'condena',
               'controla', 'destroy', 'destroza', 'duro', 'ejecuta', 'enseña', 'escarmiento', 'execute', 'fuck',
               'fusila', 'hell', 'humos', 'infierno', 'jefe', 'jode', 'learn', 'leccion', 'lesson', 'manda', 'paliza',
               'purgatorio', 'purgatory', 'sancion', 'shoot', 'teach', 'whip'),
    'random': ('aleatorio', 'azar', 'random'),
    'scraping': ('busca', 'contenido', 'content', 'descarga', 'descargar', 'descargues', 'download', 'envia', 'scrap',
                 'scrapea', 'scrapees', 'scraping', 'search', 'send'),
    'self': (('contigo', 'contra', 'ti'), ('mismo', 'ti')),
    'song_info': ('cancion', 'data', 'datos', 'info', 'informacion', 'information', 'sonaba', 'sonando', 'song', 'sono',
                  'sound', 'suena'),
    'tunnel': ('canal', 'channel', 'tunel', 'tunnel'),
    'unpunish': ('absolve', 'forgive', 'innocent', 'inocente', 'perdona', 'spare'),
    'until': ('hasta', 'until'),
    'vote': ('vote', 'voto'),
    'weather': ('atmosfera', 'atmosferico', 'calle', 'calor', 'caloret', 'clima', 'climatologia', 'cloud', 'cloudless',
                'cloudy', 'cold', 'congelar', 'congelado', 'denbora', 'despejado', 'diluvio', 'frio', 'frost', 'hielo',
                'humedad', 'llover', 'llueva', 'llueve', 'lluvia', 'nevada', 'nieva', 'nieve', 'nube', 'nubes',
                'nublado', 'meteorologia', 'rain', 'snow', 'snowfall', 'snowstorm', 'sol', 'solano', 'storm', 'sun',
                'temperatura', 'tempo', 'tiempo', 'tormenta', 'ventisca', 'weather', 'wetter')
}

SCRAPING_PHRASES = ('Analizando...', 'Buscando...', 'Hackeando internet... 👀', 'Rebuscando en la web...',
                    'Robando cosas...', 'Scrapeando...', 'Scraping...')
