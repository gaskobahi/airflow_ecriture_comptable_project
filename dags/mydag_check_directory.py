from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
import sys
import os

def check_exist_directory(**kwargs)->bool:
    """
    Vérifie l'existence d'un répertoire et écrit dans un fichier de log 
    avec la date du jour dans le nom du fichier.

    Paramètres :
    - chemin_repertoire (str) : Le chemin du répertoire à vérifier.
    """
    result:bool=False
    chemin_repertoire = "/opt/airflow/dags"  # Le chemin dans le conteneur

    # Génération du nom du fichier de log avec la date actuelle
    date_aujourdhui = datetime.now().strftime("%Y-%m-%d")
    nom_fichier_log = "log_{date_aujourdhui}.txt"
    
    print(f"[INFO] {datetime.now()} - Vérification du répertoire : {chemin_repertoire}")
    print('opopopopop',os.path.exists(chemin_repertoire))
    # Vérifie l'existence du répertoire
    if os.path.exists(chemin_repertoire) and os.path.isdir(chemin_repertoire):
        message = f"[INFO] {datetime.now()} - Le répertoire '{chemin_repertoire}' existe.\n"
        result= True
    else:
        message = f"[ERREUR] {datetime.now()} - Le répertoire '{chemin_repertoire}' n'existe pas.\n"
        result= False

    # Création ou écriture dans le fichier log
    with open(nom_fichier_log, "a") as fichier_log:
        fichier_log.write(message)

    print('jhjhjhjh',message)  # Affiche le message dans les logs Airflow
    return result

def check_directory():
    # Vérifie le contenu du répertoire monté dans le conteneur
    import os
    
    chemin_repertoire = '/opt/airflow/dags'  # Le chemin dans le conteneur
    if os.path.exists(chemin_repertoire):
        print(f"Le répertoire existe : {chemin_repertoire}")
        print("Contenu du répertoire : ", os.listdir(chemin_repertoire))
    else:
        print(f"Le répertoire n'existe pas : {chemin_repertoire}")



# Définition du DAG
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'retries': 1,
}

with DAG(
    dag_id='verifier_repertoire_dag',
    default_args=default_args,
    description='DAG pour vérifier l\'existence d\'un répertoire',
    schedule=timedelta(hours=30),  # Nouveau paramètre
    start_date=datetime(2025, 1, 27),
    catchup=False,
    tags=['boris', 'bahi'],
) as dag:

    # Définir la tâche avec PythonOperator
    verifier_repertoire_task = PythonOperator(
        task_id='verifier_et_log_task',
        python_callable=check_exist_directory
        #op_kwargs={'chemin_repertoire':'/opt/airflow/files'},  # Remplacer par votre chemin
    )

 # Définir la tâche avec PythonOperator
    verifier_repertoire_task2 = PythonOperator(
        task_id='verifier_et_log_task2',
        python_callable=check_directory
        #op_kwargs={'chemin_repertoire':'/opt/airflow/files'},  # Remplacer par votre chemin
    )

    # Ordre des tâches (ici, une seule tâche)
    verifier_repertoire_task >> verifier_repertoire_task2
