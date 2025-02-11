from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator

# Fonction Python exécutée par les tâches
def print_hello():
    print("✅ pymysql is working!")

def print_goodbye():
    print("Goodbye, world!")

# Définition du DAG
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(days=1),
}

with DAG(
    'my_first_dag',  # Identifiant unique du DAG
    default_args=default_args,
    description='Un DAG simple pour dire Bonjour et Au revoir',
    schedule=timedelta(days=30),  # Nouveau paramètre
    start_date=datetime(2025, 1, 26),  # Date de début du DAG
    catchup=False,  # Empêche l'exécution rétroactive des tâches
    tags=['boris', 'bahi'],  # Tags pour organiser vos DAGs
) as dag:

    # Définition des tâches
    task_hello = PythonOperator(
        task_id='say_hello',  # Identifiant unique de la tâche
        python_callable=print_hello,  # Fonction à exécuter
    )

    task_goodbye = PythonOperator(
        task_id='say_goodbye',
        python_callable=print_goodbye,
    )

    # Définir l'ordre d'exécution des tâches
    task_hello >> task_goodbye  # "say_hello" sera exécutée avant "say_goodbye"