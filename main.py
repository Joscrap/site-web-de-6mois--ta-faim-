#Les import
from flask import Flask, render_template, request, url_for, redirect, session
from flask import jsonify

# on importe os, pour sécuriser le cookie de session
import os
#crypter les mots de passe dans la bdd
import bcrypt  

#on import mongo db
import pymongo 
#pour gére les ObjectId
from bson.objectid import ObjectId

#sécuriter pour les images
from werkzeug.utils import secure_filename
#heur
from datetime import datetime
# Agréger les favoris avec un compteur (combien de membres ont mis en favori)
from collections import Counter

#on import le .env pour sécuriser la connection a la base de donné
from dotenv import load_dotenv
load_dotenv()

mongo_uri = os.getenv("MONGO_URI")

#connexion a la base de données
mongo = pymongo.MongoClient(mongo_uri)
#créer notre apli flask
app = Flask(__name__)

#Cookie de session utilisateur
#app.secret_key = os.urandom(24)
#app.secret_key = "1" #pour quand je code
app.secret_key = os.getenv("SECRET_KEY")



def get_user():
    if 'util' not in session:
        return None
    
    user = mongo.ta_faim.utilisateur.find_one({'nom': session['util']})

    if not user:
        session.clear()
        return None
    
    return user




#######################
### PAGE DU SITE ######
#######################



#accueil de connexion
@app.route('/')
def index():
    # Vérifier si l'utilisateur est connecté
    if 'util' in session:
        user = mongo.ta_faim.utilisateur.find_one({'nom': session['util']})
        
        # Si l'utilisateur existe
        if user:
            # S'il n'est pas encore dans un groupe, rediriger vers connexion_groupe
            if user.get('team') is None:
                return redirect(url_for('connexion_groupe'))
            # Sinon, il a un groupe → rediriger vers accueil
            return redirect(url_for('accueil'))

    # Personne n'est connecté → afficher la page publique
    return render_template('index.html')


###########################################################################################################################


# page d'accueil
@app.route('/accueil')
def accueil():
    
    user = get_user()
    
    if not user:
        return redirect(url_for('login'))
    
    # on vérifie si il a une team
    if user.get('team') is None:
        # si non on l'envoie vers la page de connexion de groupe
        return redirect(url_for('connexion_groupe'))

    annonces = list(mongo.ta_faim.annonces.find({}))

    # On récupère sa liste de favoris pour savoir si cette annonce est déjà en favori
    # Ça permettra au template d'afficher ❤️ ou 🤍 selon le cas
    user_favoris = user.get('favoris', [])

    # 👉 si c’est PAS une liste, on la transforme en liste
    if not isinstance(user_favoris, list):
        user_favoris = [user_favoris]


    # On cherche dans la collection "annonces" toutes les annonces
    # dont l'_id est dans la liste des favoris de l'utilisateur
    # $in permet de faire un "WHERE _id IN (...)" comme en SQL
    annonces_fav = list(mongo.ta_faim.annonces.find({'_id': {'$in': user_favoris}}))

    return render_template('accueil.html', nom=user['nom'], annonces=annonces, annonces_fav=annonces_fav, user_favoris=user_favoris)
    

###########################################################################################################################


# page pour afficher les annonce
@app.route('/annonce/<id_annonces>')
def annonce(id_annonces):

    user = get_user()
    
    if not user:
        return redirect(url_for('login'))
    
    # on vérifie si il a une team
    if user.get('team') is None:
        # si non on l'envoie vers la page de connexion de groupe
        return redirect(url_for('connexion_groupe'))


    # On accède à la collection "annonces"
    db_annonces = mongo.ta_faim.annonces

    # On récupère l'annonce dont l'_id correspond à celui passé dans l'URL
    annonces = db_annonces.find_one({"_id": ObjectId(id_annonces)})
    
    # On récupère sa liste de favoris pour savoir si cette annonce est déjà en favori
    # Ça permettra au template d'afficher ❤️ ou 🤍 selon le cas
    user_favoris = user.get('favoris', [])

    # 👉 si c’est PAS une liste, on la transforme en liste
    if not isinstance(user_favoris, list):
        user_favoris = [user_favoris]


    return render_template("annonce_grand.html", annonces=annonces, nom=session['util'], user_favoris=user_favoris)


###########################################################################################################################


#logeout
@app.route('/logout')
def logout():
    session.clear()
    print("logout")
    return redirect(url_for('index'))


###########################################################################################################################


@app.route('/profil')
def profil():

    user = get_user()
    
    if not user:
        return redirect(url_for('login'))
    
    # on vérifie si il a une team
    if user.get('team') is None:
        # si non on l'envoie vers la page de connexion de groupe
        return redirect(url_for('connexion_groupe'))
    
    nom = user.get('nom')
    groupe = user.get('team')
    bio = user.get('bio', "")

    tableau_fav = user.get('favoris', [])
    nb_fav = len(tableau_fav)
    print(nb_fav)
    

    return render_template("profil.html", user=user, nb_fav=nb_fav)



###########################################################################################################################


@app.route('/favori')
def favorie():

    user = get_user()
    
    if not user:
        return redirect(url_for('login'))
    
    # on vérifie si il a une team
    if user.get('team') is None:
        # si non on l'envoie vers la page de connexion de groupe
        return redirect(url_for('connexion_groupe'))
    
    # On récupère sa liste de favoris pour savoir si cette annonce est déjà en favori
    # Ça permettra au template d'afficher ❤️ ou 🤍 selon le cas
    user_favoris = user.get('favoris', [])

    # 👉 si c’est PAS une liste, on la transforme en liste
    if not isinstance(user_favoris, list):
        user_favoris = [user_favoris]


    # On cherche dans la collection "annonces" toutes les annonces
    # dont l'_id est dans la liste des favoris de l'utilisateur
    # $in permet de faire un "WHERE _id IN (...)" comme en SQL
    annonces_fav = list(mongo.ta_faim.annonces.find({'_id': {'$in': user_favoris}}))

    # On envoie les annonces favorites au template pour les afficher
    return render_template("favori.html", nom=session['util'], annonces_fav=annonces_fav, user_favoris=user_favoris)



###########################################################################################################################
###########################################################################################################################


#######################
####### admin #########
#######################


@app.route('/admin/back_accueil')
def admin():
    if 'util' in session and session['role'] == 'admin':
        return render_template("admin/back_accueil.html", nom=session['util'])
    else:
        return "Accès refusé. Vous devez être connecté en tant qu'administrateur."

@app.route('/admin/back_utilisateur')
def admin_utilisateur():
    if 'util' in session and session['role'] == 'admin':
        db_utili = mongo.ta_faim.utilisateur
        utili = db_utili.find({})

        return render_template("admin/back_utilisateur.html", utili=utili , nom=session['util'])
    else:
        return "Accès refusé. Vous devez être connecté en tant qu'administrateur."

@app.route('/admin/back_annonce')
def admin_annonce():
    if 'util' in session and session['role'] == 'admin':
        db_utili = mongo.ta_faim.annonces
        annnonces = db_utili.find({})

        return render_template("admin/back_annonce.html", annnonces=annnonces)
    else:
        return "Accès refusé. Vous devez être connecté en tant qu'administrateur."




#######################
#### rout admin #######
#######################

#route d'un utilisateur
@app.route('/utilisateur/<id_post>')
def recup_utilisateur(id_post):

    user = get_user()
    if not user:
        return redirect(url_for('login'))
    
    # on vérifie si il a une team
    if user.get('team') is None:
        # si non on l'envoie vers la page de connexion de groupe
        return redirect(url_for('connexion_groupe'))
    
    db_utili = mongo.ta_faim.utilisateur
    user = db_utili.find_one({"_id": ObjectId(id_post)})
    
    return render_template("profil.html", user=user)



# Route de modif d'utili (Si l'on a déjà un compte)
@app.route('/modif_utilis/<id_post>', methods=['POST', 'GET'])
def modif(id_post):
    if 'util' in session and session['role'] == 'admin':
        db_utilis = mongo.ta_faim.utilisateur
        utilis = db_utilis.find_one({"_id": ObjectId(id_post)})

        #si methods GET
        if request.method == 'GET':
            return render_template('/admin/modif_utilisateur.html', utilis=utilis)
        #sinon methods POST
        else:
            nom = request.form['utilisateur']
            team = request.form['team']
            role = request.form['role']
            bio = request.form['bio']
            db_utilis.update_one({"_id" : ObjectId(id_post)},
                             {"$set" :{ 
                              "nom" : nom,
                              "role" : role,
                              "team" : team,
                              "bio" : bio
                            }})
            return redirect(url_for("admin_utilisateur"))
    else:
        return "Accès refusé. Vous devez être connecté en tant qu'administrateur."

#route pour suprimer utili
@app.route('/suprimer_utili/<id_post>', methods=['POST'])
def suprimer_utili(id_post):
    if 'util' in session and session['role'] == 'admin':
        db_utilis = mongo.ta_faim.utilisateur
        utilis = db_utilis.delete_one({"_id": ObjectId(id_post)})
        return redirect(url_for("admin_utilisateur", message="L'utilisateur est bien suprimer", utilis=utilis))
    else:
        return "Accès refusé. Vous devez être connecté en tant qu'administrateur."

#route pour suprimer annonce
@app.route('/suprimer_annonce/<id_post>', methods=['POST'])
def suprimer_annonce(id_post):
    if 'util' in session and session['role'] == 'admin':
        db_utilis = mongo.ta_faim.annonces
        annonce = db_utilis.delete_one({"_id": ObjectId(id_post)})
        return redirect(url_for("admin_annonce", message="L'annonce est bien suprimer", annonce=annonce))
    else:
        return "Accès refusé. Vous devez être connecté en tant qu'administrateur."






#######################
### UTILISATEUR #######
#######################

# Route de login (Si l'on a déjà un compte)
@app.route('/login', methods=['POST', 'GET'])
def login():
    
    # Si on essaye de se connecter
    if request.method == 'POST':

        # On appelle la table utilisateur de la bdd
        db_utils = mongo.ta_faim.utilisateur
        util = db_utils.find_one({'nom': request.form['utilisateur']})

        # Si l'utilisateur existe
        if util:
            # On vérifie si le mot de passe est bon
            if bcrypt.checkpw(request.form['mot_de_passe'].encode('utf_8'),util['mdp']):

                session['util'] = request.form['utilisateur']
                session['role'] = util['role']

                user = mongo.ta_faim.utilisateur.find_one({
                'nom': session['util']
                })

                #on vérifie si a pas déjà un groupe pour l'envoyer directement sur la page d'accueil
                team = user.get('team')
                db_team = mongo.ta_faim.team

                if team is None:
                    return redirect(url_for("create_groupe"))

                veri_team = db_team.find_one({'nom': team})

                if veri_team is None:
                    return redirect(url_for("create_groupe"))

                return redirect(url_for("accueil"))
                
            # Sinon on envoie un message d'erreur mot de passe incorrect
            else:
                return render_template('login.html', erreur="Le mot de passe est incorrect")
        # Sinon l'utilisateur n'existe pas
        else:
            return render_template('login.html', erreur="L'utilisateur n'existe pas")
    else:
        return render_template('login.html')


###########################################################################################################################


#page de registre
@app.route('/register', methods=['POST', 'GET'])
def register():

    #si on essaye de soummettre un formulaire
    if request.method == 'POST':
        #vérifier qu'un utilisateur du meme nom n'existe pas
        db_utili = mongo.ta_faim.utilisateur
        # si l'utilisateur existe déjà
        if (db_utili.find_one({'nom' : request.form['utilisateur']})):
            return render_template('register.html', erreur="Le nom d'utilisateur existe déjà")
        
        #sinon on crée l'utilisateur
        else:
            # on vérifie si le mot de passe est le même que la confiramtion
            if (request.form['mot_de_passe']) == (request.form['verif_mot_de_passe']):
                # on va cripter le mot de passse 
                mdp_encrypte = bcrypt.hashpw(request.form['mot_de_passe'].encode('utf-8'), bcrypt.gensalt())
                # j'ajoute l'utilisateur dans ma bdd
                db_utili.insert_one({
                    'nom' : request.form['utilisateur'],
                    'mdp' : mdp_encrypte,
                    'team' : None,
                    'role' : 'abonné',
                    'favoris' : []
                })
                #on le connecte avec un cookie de session
                session['util'] = request.form['utilisateur']
                session['role'] = 'abonné'
                #on retourne sur la page d'acceil
                return redirect(url_for('create_groupe'))

            else:
                return render_template('register.html', erreur="Les mots de passe ne sont pas identiques")

    else:
        return render_template('register.html')


###########################################################################################################################


#page connecxion groupe
@app.route('/connexion_groupe', methods=['POST', 'GET'])
def connexion_groupe():

    if 'util' not in session:
        return redirect(url_for('login'))
    
    # Si on essaye de se connecter
    if request.method == 'POST':

        # On appelle la table utilisateur de la bdd
        db_team = mongo.ta_faim.team
        db_utili = mongo.ta_faim.utilisateur

        team = db_team.find_one({'nom': request.form['team']})

        # Si la team existe
        if team:

            # On vérifie si le mot de passe est bon
            if bcrypt.checkpw(request.form['mot_de_passe'].encode('utf_8'),team['mdp']):
                db_utili = mongo.ta_faim.utilisateur
                
                """
                db_team.update_one(
                    {'nom': request.form['team']},          # filtre : quelle team modifier
                    {'$addToSet': {'perso': session['util']}}  # modification : ajouter l'utilisateur
                )
                """

                db_utili.update_one(
                    {'nom': session['util']},
                    {'$set': {'team': request.form['team']}}
                )
                return redirect(url_for("accueil"))
            
            # Sinon on envoie un message d'erreur mot de passe incorrect
            else:
                return render_template('connexion_groupe.html', erreur="Le mot de passe est incorrect")
            
        # Sinon l'utilisateur n'existe pas
        else:
            return render_template('connexion_groupe.html', erreur="Le groupe n'existe pas")
    else:
        return render_template('connexion_groupe.html')


###########################################################################################################################


@app.route('/create_groupe', methods=['POST', 'GET'])
def create_groupe():

    if 'util' not in session:
        return redirect(url_for('login'))
    
    #si on essaye de soummettre un formulaire
    elif request.method == 'POST':
        #vérifier qu'une team du meme nom n'existe pas
        db_team = mongo.ta_faim.team
        db_utili = mongo.ta_faim.utilisateur
        # si la team existe déjà
        if (db_team.find_one({'nom' : request.form['team']})):
            return render_template('create_groupe.html', erreur="Le nom de la team existe déjà")
        
        #sinon on crée la team
        else:
            # on vérifie si le mot de passe est le même que la confiramtion
            if (request.form['mot_de_passe']) == (request.form['verif_mot_de_passe']):
                # on va cripter le mot de passse 
                mdp_encrypte = bcrypt.hashpw(request.form['mot_de_passe'].encode('utf-8'), bcrypt.gensalt())
                # j'ajoute la team dans ma bdd
                db_team.insert_one({
                    'nom' : request.form['team'],
                    'mdp' : mdp_encrypte
                    #'perso' : [session['util']]
                })
                #on ajoute le nom de la team dans les info de l'utilisateur
                db_utili.update_one(
                    {'nom': session['util']},
                    {'$set': {'team': request.form['team']}
                })
                #on retourne sur la page d'acceil
                return redirect(url_for('accueil'))

            else:
                return render_template('create_groupe.html', erreur="Les mots de passe ne sont pas identiques")
    else:
        return render_template('create_groupe.html')


###########################################################################################################################

import cloudinary
import cloudinary.uploader
from cloudinary.utils import cloudinary_url

def upload(image):
    api_sec = os.getenv("CLOUDINARY_SEC")
    api = os.getenv("CLOUDINARY")


    # Configuration       
    cloudinary.config( 
        cloud_name = "dsoscu8cn", 
        api_key = api, 
        api_secret = api_sec, # Click 'View API Keys' above to copy your API secret
        secure=True
    )

    # Upload an image
    upload_result = cloudinary.uploader.upload(image)

    return upload_result["secure_url"]

###########################################################################################################################



# Autoriser seulement certains types de fichiers
ALLOWED_EXTENSIONS = {'png', 'jpg'}

def allowed_file(filename):
    #rsplit('.', 1)[1] → prend la partie après le dernier point (l’extension)
    #lower() → rend la vérification insensible à la casse.
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/nouvelle_annonce', methods=['POST', 'GET'])
def nouvelle_annonce():

    if 'util' not in session:
        return redirect(url_for('login'))
    
    #si on essaye de soummettre un formulaire
    if request.method == 'POST':     
        #Récupère le fichier uploadé (<input type="file" name="image">).
        image = request.files.get('image')
        titre = request.form.get('titre')
        description = request.form.get('description')

        #Vérifie :qu’un fichier existe et qu’il n’est pas vide
        if not image or image.filename == '':
            return render_template('création_annonce.html', erreur="Vous devez ajouter une image !")

        if not titre or titre.strip() == "":
            return render_template('création_annonce.html', erreur="Titre obligatoire")

        # vérifie le format du fichier (fonction au dessus)
        if not allowed_file(image.filename):
            return render_template('création_annonce.html', erreur="Extension non autorisée. Seuls les JPG et PNG sont acceptés")


        image_url = upload(image)

        # j'ajoute l'annonce dans ma bdd
        mongo.ta_faim.annonces.insert_one({
            'titre' : titre,
            'auteur' : session.get('util'),
            'description' : description,
            'img' : image_url,
            'date': datetime.utcnow()             
        })
        #on retourne sur la page d'acceil
        return redirect(url_for('accueil'))
    else:
        return render_template('création_annonce.html')


###########################################################################################################################


@app.route('/quitter_team', methods=['POST'])
def quitter_team():
    
    db_utili = mongo.ta_faim.utilisateur

    db_utili.update_one(
        {'nom': session['util']},
        {'$set': {'team': None}}
    )

    return redirect(url_for('connexion_groupe'))


###########################################################################################################################


@app.route('/update_bio', methods=['POST'])
def update_bio():

    nouvelle_bio = request.form.get('bio')

    mongo.ta_faim.utilisateur.update_one(
        {'nom': session['util']},
        {'$set': {'bio': nouvelle_bio}}
    )

    return redirect(url_for('profil'))

###########################################################################################################################


# Route pour ajouter ou retirer une annonce des favoris
# <id_annonce> est l'identifiant unique de l'annonce passé dans l'URL
@app.route('/toggle_favori/<id_annonce>', methods=['POST'])
def toggle_favori(id_annonce):
    
    user = get_user()
    if not user:
        return redirect(url_for('login'))
    if user.get('team') is None:
        return redirect(url_for('connexion_groupe'))

    db_utili = mongo.ta_faim.utilisateur
    
    # On récupère sa liste de favoris (si elle n'existe pas encore, on retourne une liste vide)
    favoris = user.get('favoris', [])

    # MongoDB stocke les IDs sous forme d'ObjectId, pas de simples strings
    # On convertit donc l'id reçu (string) en ObjectId pour pouvoir le comparer
    oid = ObjectId(id_annonce)

    if not isinstance(favoris, list):
        favoris = [favoris]

    # Si l'annonce est déjà dans les favoris → on la retire
    if oid in favoris:
        db_utili.update_one(
            {'nom': session['util']},   # on cible l'utilisateur connecté
            {'$pull': {'favoris': oid}} # $pull retire l'élément de la liste
        )
        
    # Sinon → on l'ajoute
    else:
        db_utili.update_one(
            {'nom': session['util']},          # on cible l'utilisateur connecté
            {'$addToSet': {'favoris': oid}}    # $addToSet ajoute sans créer de doublon
        )  
    
    # On demande à Flask : "Sur quelle page était l'utilisateur avant de cliquer ?"
    page_precedente = request.referrer

    # S'il y a bien une page précédente (le navigateur a fourni l'info)
    if page_precedente:
        return redirect(page_precedente)
    
    # Solution de secours : 
    # Si le navigateur de l'utilisateur bloque cette information par sécurité,
    # on le renvoie par défaut sur la page de l'annonce.
    else:
        return redirect(url_for('annonce', id_annonces=id_annonce))

###########################################################################################################################


@app.route('/recherche', methods=['POST'])
def recherche():
    user = get_user()
    if not user:
        return redirect(url_for('login'))
    if user.get('team') is None:
        return redirect(url_for('connexion_groupe'))
    
    query = request.form['query']
    db_annonce = mongo.ta_faim.annonces
    annonces = db_annonce.aggregate([{
        '$match': {
            'titre': {
                '$regex': query,
                '$options': 'i'
            }
        }
    }])

    user_favoris = user.get('favoris', [])

    
    return render_template('resultats.html', query=query, annonces=list(annonces), user_favoris=user_favoris)

###########################################################################################################################
############################ groupe de l'enfer ############################################################################
###########################################################################################################################



@app.route('/accueil_group')
def groupe():
    user = get_user()
    if not user:
        return redirect(url_for('login'))
    if user.get('team') is None:
        return redirect(url_for('connexion_groupe'))

    team_name = user.get('team')
    team = mongo.ta_faim.team.find_one({'nom': team_name})

    # Récupérer tous les membres de la team
    membres = list(mongo.ta_faim.utilisateur.find({'team': team_name}))

    # ── FAVORIS DU GROUPE ──────────────────────────────────────────────────────
    # On agrège tous les favoris de tous les membres avec un compteur
    tous_les_favoris = []
    for m in membres:
        favs = m.get('favoris', [])
        if not isinstance(favs, list): #sécurité MongoDB ( si pas liste on le transforme quand même en liste pour éviter un crash )
            favs = [favs]
        tous_les_favoris.extend(favs) #extend ajoute tous les éléments d'une liste dans une autre

    #Counter est une structure Python qui compte les occurrences (2 personne on 1 annonce en fav alors on comte 2)
    compteur_favoris = Counter(tous_les_favoris)
    # Trier par popularité et garder les 5 premiers
    ids_top = [fav_id for fav_id, _ in compteur_favoris.most_common(5)] #most_common(5) retourne les 5 plus fréquents sous forme de tuples (ObjectId, count)
    #[fav_id for fav_id, _ in ...] décompresse chaque tuple et garde seulement l'ObjectId (le _ est une convention Python pour dire "cette variable ne m'intéresse pas")
    #en gros il mes les plus populaire tout devant

    annonces_fav = []
    if ids_top:
        #$in récupère en une seule requête toutes les annonces dont l'_id est dans la liste
        annonces_raw = list(mongo.ta_faim.annonces.find({'_id': {'$in': ids_top}}))
        # Ajouter le score (nombre de membres qui ont mis en favori)
        for a in annonces_raw:
            a['score'] = compteur_favoris.get(a['_id'], 0) #on ajoute un champ score qui est = au nb de personne du groupe qui l'on en fav
        # Trier par score décroissant
        annonces_fav = sorted(annonces_raw, key=lambda x: x['score'], reverse=True) #lambda x: x['score'] est une mini-fonction qui dit : "pour comparer deux annonces, regarde leur champ score"
        #reverse=True pour avoir les scores les plus hauts en premier

    # ── VOTES DU GROUPE ────────────────────────────────────────────────────────
    # Les votes sont stockés dans le document team sous la forme :
    # { 'votes': { '<str(ObjectId)>': ['alice', 'thomas'], ... } }
    votes_data = team.get('votes', {})
 
    # Récupérer les annonces candidates au vote (celles qui ont au moins 1 vote
    # ou toutes les annonces — ici on prend celles qui ont des votes + les top favoris)
    ids_votes = [ObjectId(id_annonce) for id_annonce in votes_data.keys()] #votes_data.keys() te donne les clés du dictionnaire c'est-à-dire les IDs des annonces proposées au vote mais sous forme de strings
    ids_candidats = list(set(ids_votes)) #set() supprime les doublons, list() le reconvertit en liste 
 
    annonces_candidats = []
    if ids_candidats: #if ids_candidats évite la requête si la liste est vide.
        annonces_candidats = list(mongo.ta_faim.annonces.find({'_id': {'$in': ids_candidats}}))
 
    # Construire un résumé des votes pour le template
    # len(v) donne la taille de chaque liste
    # sum(...) additionne tout : 2 + 1 = 3 votes au total (Ce total sert uniquement à calculer les pourcentages pour les barres de progression dans le fronte)
    total_votes = sum(len(vote) for vote in votes_data.values())
    votes_resume = {}

    for annonce_id_str, votants in votes_data.items(): #.items() itère sur le dictionnaire en donnant à chaque tour la clé ET la valeur en même temps (id annonce + perso qui a voter)
        votes_resume[annonce_id_str] = {
            'count': len(votants), #count — combien de personnes ont voté
            'user_voted': session['util'] in votants, #user_voted — est-ce que TOI (l'utilisateur connecté) tu as voté pour cette annonce (True ou False)
            'pct': round(len(votants) / total_votes * 100) if total_votes > 0 else 0, #pct — le pourcentage pour la barre de progression dans le fronte
            #if total_votes > 0 else 0 est une sécurité : si personne n'a voté, total_votes vaut 0 et diviser par 0 ferait crasher Python
            # round arrondi au pair le plus proche (règle Python)
        }
 
    return render_template(
        'accueil_group.html',
        team=team_name,
        nom=session['util'],
        membres=membres,
        annonces_fav=annonces_fav,
        annonces_candidats=annonces_candidats,
        votes_resume=votes_resume,
    )






##########################################################################################################################
####################################### route ############################################################################
##########################################################################################################################
 
 
@app.route('/voter/<id_annonce>', methods=['POST'])
def voter(id_annonce):
    """
    Toggle le vote de l'utilisateur connecté pour une annonce donnée.
    - Si l'utilisateur n'a pas encore voté pour cette annonce → on ajoute son nom
    - Si l'utilisateur a déjà voté pour cette annonce → on retire son nom (dé-vote)
    - Si l'utilisateur avait voté pour une AUTRE annonce → on retire l'ancien vote
      et on ajoute le nouveau (un seul vote par personne)
    """
 
    user = get_user()
    if not user:
        return redirect(url_for('login'))
 
    team_name = user.get('team')
    if not team_name:
        return redirect(url_for('connexion_groupe'))
 
    nom_util = session['util']
    team = mongo.ta_faim.team.find_one({'nom': team_name})
    votes_data = team.get('votes', {})

    # Chercher si l'utilisateur a déjà voté pour une autre annonce
    for annonce_id_str, votants in votes_data.items():#annonce_id_str = l'annonce stocker dans vote, votants = perso qui a voter sur cette annonce
        if nom_util in votants and annonce_id_str != id_annonce:
            # Retirer l'ancien vote
            mongo.ta_faim.team.update_one(
                {'nom': team_name},
                {'$pull': {f'votes.{annonce_id_str}': nom_util}}
            )
            break

    # Toggle le vote sur l'annonce ciblée
    votants_actuels = votes_data.get(id_annonce, []) #On regarde qui a déjà voté pour l'annonce au moment où la page a été chargée
 
    if nom_util in votants_actuels:
        # Dé-voter
        mongo.ta_faim.team.update_one(
            {'nom': team_name},
            {'$pull': {f'votes.{id_annonce}': nom_util}}
        )
    else:
        # Voter (addToSet évite les doublons)
        mongo.ta_faim.team.update_one(
            {'nom': team_name},
            {'$addToSet': {f'votes.{id_annonce}': nom_util}}
        )
 
    return redirect(url_for('groupe'))
 

###########################################################################################################################
 
 
@app.route('/proposer_vote/<id_annonce>', methods=['POST'])
def proposer_vote(id_annonce):
    """
    Ajoute une annonce comme candidate au vote du groupe
    (initialise son compteur à [] si elle n'est pas encore dans votes).
    """
 
    user = get_user()
    if not user:
        return redirect(url_for('login'))
 
    team_name = user.get('team')
    if not team_name:
        return redirect(url_for('connexion_groupe'))
 
    team = mongo.ta_faim.team.find_one({'nom': team_name})
    votes_data = team.get('votes', {})
 
    if id_annonce not in votes_data:
        mongo.ta_faim.team.update_one(
            {'nom': team_name},
            {'$set': {f'votes.{id_annonce}': []}}
        )
 
    return redirect(url_for('groupe'))
 
 
###########################################################################################################################
 
 
@app.route('/reset_votes', methods=['POST'])
def reset_votes():
    """
    Remet à zéro tous les votes du groupe (à utiliser après avoir choisi un resto).
    Réservé à un usage admin ou chef de groupe.
    """
 
    user = get_user()
    if not user:
        return redirect(url_for('login'))
 
    team_name = user.get('team')
    if not team_name:
        return redirect(url_for('connexion_groupe'))
 
    mongo.ta_faim.team.update_one(
        {'nom': team_name},
        {'$set': {'votes': {}}}
    )
 
    return redirect(url_for('groupe'))




# execution
app.run(host='0.0.0.0', port=81)