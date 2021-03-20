#
# ------------------------------------------------------------------------------------------------------------------
# IT IS BETTER TO WORK WITH OBJECT-ORIENTED PROGRAMMING (CLASSES) TO PERSONALIZE THE WORK
# TO IMPORT THE INFORMATION FROM THE OTHER PYTHON PROGRAMS (.py), I DO IT LIKE THIS: import my_program_name.py
# with the above, I know the variables of said programs, here where I am calling them
# ------------------------------------------------------------------------------------------------------------------

# This is Main function.

# Extracting streaming data from Twitter, pre-processing, and loading into Postgres
import credentials # Import api/access_token keys from credentials.py
import settings # Import related setting constants from settings.py 

import re
import tweepy
import time
from sqlalchemy import create_engine
from textblob import TextBlob
# Streaming With Tweepy 
# http://docs.tweepy.org/en/v3.4.0/streaming_how_to.html#streaming-with-tweepy


# Override tweepy.StreamListener to add logic to on_status
class TwStreamListener(tweepy.StreamListener):
    '''
    Tweets are known as “status updates”. So the Status class in tweepy has properties describing the tweet.
    https://developer.twitter.com/en/docs/tweets/data-dictionary/overview/tweet-object.html
    '''
    print("ENTRÓ A: TwStreamListener()")
    #engine = create_engine('postgresql://postgres:password@host:5432/database')#conexion a la base de datos
    #engine = create_engine('postgresql://postgres:postgres@***AWS-RDS***:5432/twitterdb')#conexion a la base de datos
    
    #DATABASE connection (twitterdb2 is a table inside uao_team18):
    host = 'xxxx'                                                                 #AWS RDS instance
    port = 5432                                                                   #default port
    user = 'xxxx'                                                                 #database user
    password = 'xxxx'                                                             #database password
    database = 'xxxx'                                                             #database name
    engine = create_engine(f'postgresql://{user}:{password}@{host}:{port}/{database}')  #database connection (only once)

    
    auth  = tweepy.OAuthHandler(credentials.API_KEY, credentials.API_SECRET_KEY)
    runtime = 10 #para trabajar con carga suave en la capa gratuita de AWS RDS (10 segundos)

    def __init__(self):#para inicializar (recordar la teoría del curso de edX del MIT de Python, porque estas funciones son propias de la clase que se está usando, algo así como el main)
        '''
        Check if this table exits. If not, then create a new one.
        '''
        print("ENTRÓ A: __init__()")
        try:
            self.start_time = time.time()
            self.limit_time = self.runtime
            self.engine.connect()
            self.mydb = self.engine.raw_connection()
            self.mycursor = self.mydb.cursor()#debo trabajar con esto para poder hacer insert a la base de datos
            self.mycursor.execute("""
                SELECT COUNT(*)
                FROM information_schema.tables
                WHERE table_name = '{0}'
                """.format(settings.TABLE_NAME))#para validar si existe o no la tabla en la base de datos (si existe, solo insertará info ahí, si no existe, entonces creará la tabla donde se insertará la info)
            if self.mycursor.fetchone()[0] != 1:
                self.mycursor.execute("CREATE TABLE {} ({})".format(settings.TABLE_NAME, settings.TABLE_ATTRIBUTES))
                self.mydb.commit()
            self.mycursor.close()
        except Exception as error:
            print("Problem connecting to the database: ",error)
    
    def connect(self):#funcion personalizada que se crea (por eso NO va así: ___   ___)
        '''
        Connecting to the API.
        '''
        print("ENTRÓ A: connect()")
        self.auth.set_access_token(credentials.ACCESS_TOKEN, credentials.ACCESS_TOKEN_SECRET)
        self.api = tweepy.API(self.auth)
        self.myStream = tweepy.Stream(auth = self.api.auth, listener = self)
        print("SALIÓ DE: connect()")
        return None


    def on_status(self, status):
        '''
        Extract info from tweets
        '''
        print("ENTRÓ A: on_status()")
        if status.retweeted:
            # Avoid retweeted info, and only original tweets will be received
            return True
        # Extract attributes from each tweet
        id_str = status.id_str
        created_at = status.created_at
        text = self.deEmojify(status.text)    # Pre-processing the text  
        sentiment = TextBlob(text).sentiment #este es un modelo pre-entrenado que devuelve la info de sentimiemto para usarse en Twitter
        polarity = sentiment.polarity
        subjectivity = sentiment.subjectivity
        
        user_created_at = status.user.created_at
        print("User created at: ",user_created_at)
        
        print("User Location (uncleaned): ", status.user.location)
        user_location = self.deEmojify(status.user.location)
        print("User Location (cleaned): ",user_location)
        
        print("User description (uncleaned): ", status.user.description)
        user_description = self.deEmojify(status.user.description)
        print("User description (cleaned): ",user_description)
                       
        user_followers_count =status.user.followers_count
        print("User followers count: ",user_followers_count)
        
        longitude = None #initialize
        latitude = None  #initialize
        
        if status.coordinates:#en caso de que esta info esté disponible
            longitude = status.coordinates['coordinates'][0]
            latitude = status.coordinates['coordinates'][1]
            
        retweet_count = status.retweet_count
        print("retweet_count: ",retweet_count)
        favorite_count = status.favorite_count
        print("favorite_count: ",favorite_count)
        
        print("status.text: ", status.text)
        print("Long: {}, Lati: {}".format(longitude, latitude))
        
        #importante HACER MANEJO DE ERRORES CON TRY , por ejemplo para la comexión a la base de datos
        # Store all data in PostgreSQL
        try:
            '''
            Check if this table exits. If not, then create a new one.
            '''
            self.engine.connect()
            self.mydb = self.engine.raw_connection()
            self.mycursor = self.mydb.cursor()
            sql = "INSERT INTO {} (id_str, created_at, text, polarity, subjectivity, user_created_at, user_location, user_description, user_followers_count, longitude, latitude, retweet_count, favorite_count) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)".format(settings.TABLE_NAME) #AQUI ESTOY INSERTANDO INFO A MI TABLA
            val = (id_str, created_at, text, polarity, subjectivity, user_created_at, user_location, \
                user_description, user_followers_count, longitude, latitude, retweet_count, favorite_count)
            self.mycursor.execute(sql, val)
            self.mydb.commit()
            
            #DELETING INFO TO AVOID OVERLOADING THE DASTABASE AND JUST KEEP TRACK OF THE LATEST DAILY INFO:
            delete_query = '''
            DELETE FROM {0}
            WHERE id_str IN (
                SELECT id_str
                FROM {0}
                ORDER BY created_at asc
                LIMIT 200) AND (SELECT COUNT(*) FROM twitter2) > 9600;
            '''.format(settings.TABLE_NAME)  
            
            self.mycursor.execute(delete_query)
            self.mydb.commit()
            self.mycursor.close()        
        
        
        except Exception as error:
            print("Error inserting/deleting info into/from the twitter table: ",error)                       
                       
           
        
        #VALIDANDO LOS TIEMPOS:
        if (time.time() - self.start_time) < self.limit_time:
            print("Working")
            return True #CONTINUE "ESCUCHANDO" LA INFO DE TWITTER
        else:
            print("Time Complete")
            return False #PARE DE "ESCUCHAR" LA INFO DE TWITTER
    
    
    def on_error(self, status_code):#IMPORANTE AQUI MANEJAR ERRORES
        '''
        Since Twitter API has rate limits, stop scraping data as it exceed to the thresold.
        '''
        print("ENTRÓ A: on_error()")
        if status_code == 420:
            # return False to disconnect the stream
            return False

    def clean_tweet(self, tweet): #LIMPIANDO LOS TWEETS
        ''' 
        Use simple regex statemnents to clean tweet text by removing links and special characters
        '''
        print("ENTRÓ A: clean_tweet()")
        return ' '.join(re.sub("(@[A-Za-z0-9]+)|([^0-9A-Za-z \t])|(\w+:\/\/\S+)", " ", tweet).split()) 

    def deEmojify(self,text): #QUITAR EMOJIS
        '''
        Strip all non-ASCII characters to remove emoji characters
        '''
        print("ENTRÓ A: deEmojify()")
        if text:
            return text.encode('ascii', 'ignore').decode('ascii')
        else:
            return None
    
    def disconnect(self):#DESCONEXIÓN DE LA BASE DE DATOS
        print("ENTRÓ A: disconect()")
        self.mydb.close()
        print("EJECUTÓ: disconnect.mydb.close()")
        return print("Stop Streaming")
    
        
    def run(self): #solo se activa cuando escucha la palabra "vacunas"
        print("Start Streaming---INICIANDO")#INICIALIZAR LA "ESCUCHA"
        #AQUI LE DIGO LO QUE VA A ESCUCHAR: 
        #UK (english): FUNCIONÓ BIEN PARA LA PALABRA COVID (siguiendo el ejemplo modelo) PERO DE TELEPERFORMANCE SOLO ENCONTRÓ 1 TWEET:(
        #self.myStream.filter(languages=["en"], track = settings.TRACK_WORDS,is_async=True,locations=[-6.38,49.87,1.77,55.81])
        #Colombia (spanish):NO FUNCIONó!
        #self.myStream.filter(languages=["sp"], track = settings.TRACK_WORDS,is_async=True,locations=[-74,0,-60,5])
        #US (english):the location is working but only one "teleperformance" has been caught so far (+20secs runtime needed)
        #self.myStream.filter(languages=["en"], track = settings.TRACK_WORDS,is_async=True,locations=[-120,20,-70,45])
        #Colombia (english):no hay info en ventanas de 30 segs en idioma inglés (probemos en español: tampoco hubo)
        #self.myStream.filter(languages=["en"], track = settings.TRACK_WORDS[0],is_async=True,locations=[-74,0,-60,5])
        #All over the world (english):
        #self.myStream.filter(languages=["en"], track = settings.TRACK_WORDS,is_async=True,locations=[-179,-89,179,89])
        
        #All over the world (working properly):
        #self.myStream.filter(languages=["en"], track = settings.TRACK_WORDS[0])
        self.myStream.filter(languages=["es"], track = settings.TRACK_WORDS[0]) #OJO AQUI ES es=español (en las stopwords si es "spanish")
        print('SE EJECUTÓ: self.myStream.filter(languages=["es"], track = settings.TRACK_WORDS[0]) #sp=español')
        time.sleep(self.runtime)
        print("SE EJECUTÓ: time.sleep(self.runtime)")
        self.disconnect()
        print("SE EJECUTÓ: run.disconect()")
        return None
