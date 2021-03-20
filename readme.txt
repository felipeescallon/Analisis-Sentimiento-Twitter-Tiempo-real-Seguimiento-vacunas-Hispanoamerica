- Los print() del main.py llamado por extratc_tweets.sh, se van a la basura, y a su vez el main.py llama a TwStreamListener.py (algunos print() son necesarios pero otros pueden comentarse, igual los print() no se copian en ningun lugar, asi quedó en el crontab modificado: dev/null). 

- Además, los print() del app.py llamado por el comando "nohup python3.6 app.py &" se van al archivo "nohub.out", asi que es mejor no cargarlo con mucha info (a veces innecesaria porque ya todo se muestra en la aplicación de Dash), por lo que se recomienda comentar TODOS los print().
