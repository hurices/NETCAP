import socket, sys
import threading

#définition d'un serveur réseau rudimentaire
# ce serveur attend la connexion d'un client
def poolClient(connexion, adresse, counter):
    print(f"Connesion d'un appareil depuis l'adresse: {adresse} Nombre de clients connectés: {counter}")
    try:
        messageServeur = "Bienvenue , vous vous êtes connecté avec succès"
        connexion.send(messageServeur.encode('utf-8')) #envoi du message de bienvenue au client
        messsageClient = connexion.recv(1024).decode('utf-8') #réception du message du client

        while True:

            print("Client: ", messsageClient)

            if messsageClient.upper() == "BYE" or messsageClient == "":

                print("Client déconnecté: ", adresse)
                counter -= 1

                break##FIN DE LA CONNEXION ET NOMBRE DE CLIENTS CONNECTÉS DIMINUÉ DE 1

            messageServeur = input("Serveur: ") #saisie du message à envoyer au client
            connexion.send(messageServeur.encode('utf-8')) #envoi du message au client
            messsageClient = connexion.recv(1024).decode('utf-8') #réception du message du client
    except Exception as e:
        print(f"Erreur lors de la communication avec le client: {e}")
    finally:
        connexion.close()


def creationServeur():
    # hostname = socket.gethostname()
    #la configuration du serveur
    HOST = "0.0.0.0"        #écoute sur toutes les interfaces réseau disponibles
    PORT = 8080
    counter = 0             #comteur des hôtes connectés

        ## 1) creation du socket

    monPortServeur = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        
        ## 2) liaison du socket à une adresse et un port

    try:

        monPortServeur.bind((HOST, PORT))#liaison

    except socket.error as e :

        print(f"La liaison  de socket à 'adresse {HOST} et port {PORT} a échoué: {e}")
        sys.exit() #arret du programme en cas d'erreur

    while 1:

        ## 3) attent du socket à une connexion d'un client

        print("Servuer prêt, en attente de connexion...")
        monPortServeur.listen(5) #le serveur peut gérer jusqu'à 5 connexions simultanément

        ## 4) etablissement de la connexion 

        connexion, adresse = monPortServeur.accept()
        counter += 1
        print("Client connecté depuis l'adresse: ", adresse, "Nombre de clients connectés: ", counter)

        ## 5) Dialogue avec le client

        messageServeur ="Bienvenue , vous vous êtes connecté avec succès"
        connexion.send(messageServeur.encode('utf-8')) #envoi du message de bienvenue au client
        messsageClient = connexion.recv(1024).decode('utf-8') #réception du message du client

        while True:

            print("Client: ", messsageClient)

            if messsageClient.upper() == "BYE" or messsageClient == "":

                print("Client déconnecté: ", adresse)
                counter -= 1

                break##FIN DE LA CONNEXION ET NOMBRE DE CLIENTS CONNECTÉS DIMINUÉ DE 1

            messageServeur = input("Serveur: ") #saisie du message à envoyer au client
            connexion.send(messageServeur.encode('utf-8')) #envoi du message au client
            messsageClient = connexion.recv(1024).decode('utf-8') #réception du message du client

            ## 6) fermeture de la connexion
        
        connexion.send("BYE".encode('utf-8')) #envoi du message de fin de connexion au client
        connexion.close() #fermeture de la connexion

        ch = input("Voulez-vous continuer? (o/n): ")#applictaion de regex pour vérifier la saisie de l'utilisateur
        
        if ch.lower() != 'o':

            print("Fermeture du serveur...")
            
            break
        
if __name__ == "__main__":
    creationServeur() #lancer le serveur quand le script est exécuté directement