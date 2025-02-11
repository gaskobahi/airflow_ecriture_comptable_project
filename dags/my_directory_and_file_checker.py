from pathlib import Path
from airflow import DAG
from airflow.operators.python import BranchPythonOperator
from airflow.operators.empty import EmptyOperator
from datetime import date, datetime, timedelta
import os
import mysql
import pandas as pd
from datetime import datetime
from airflow.providers.mysql.hooks.mysql import MySqlHook

from sqlalchemy import create_engine, text

import logging
import shutil



# Configuration du logging
LOG_FILE = "errors.log"
logging.basicConfig(filename=LOG_FILE, level=logging.ERROR, format="%(asctime)s - %(levelname)s - %(message)s")


# Colonnes attendues et leurs types
EXPECTED_COLUMNS = [
    'accounting_date', 'lot_number', 'type_ecriture',
    'type_document','document_number','article_number',
    'variant_code','description','package_number',
    'store_code','unit_code','created_by',
    'quantity','quantity_in_sac','quantity_invoiced',
    'remaining_quantity','quantity_reserved','lettering_writing',
    'sales_amount_actual','total_cost_actual','total_cost_not_included',
    'is_open','order_type','created_at',
    "sequence_number",'kor_by_reception','kor_input'
    ]
        
COLUMN_TYPES = {
    EXPECTED_COLUMNS[0]: date,EXPECTED_COLUMNS[1]: str, EXPECTED_COLUMNS[2]: str,
    EXPECTED_COLUMNS[3]: str,EXPECTED_COLUMNS[4]: str, EXPECTED_COLUMNS[5]: str,
    EXPECTED_COLUMNS[6]: str,EXPECTED_COLUMNS[7]: str,EXPECTED_COLUMNS[8]: str,
    EXPECTED_COLUMNS[9]: str,EXPECTED_COLUMNS[10]: str,EXPECTED_COLUMNS[11]: str,
    EXPECTED_COLUMNS[12]: float,EXPECTED_COLUMNS[13]: float,EXPECTED_COLUMNS[14]: float,
    EXPECTED_COLUMNS[15]: str,EXPECTED_COLUMNS[16]: float,EXPECTED_COLUMNS[17]: float,
    EXPECTED_COLUMNS[18]: float,EXPECTED_COLUMNS[19]: float,EXPECTED_COLUMNS[20]: float,
    EXPECTED_COLUMNS[21]: str,EXPECTED_COLUMNS[22]: str,EXPECTED_COLUMNS[23]: datetime,
    EXPECTED_COLUMNS[24]: int,EXPECTED_COLUMNS[25]: float,EXPECTED_COLUMNS[26]: float,
}

RENAMED_COLUMNS={
    "Date comptabilisation": EXPECTED_COLUMNS[0],"N° lot": EXPECTED_COLUMNS[1],"Type écriture":EXPECTED_COLUMNS[2],
    "Type document":EXPECTED_COLUMNS[3],"N° document":EXPECTED_COLUMNS[4],"N° article":EXPECTED_COLUMNS[5],
    "Code variante":EXPECTED_COLUMNS[6],"Description":EXPECTED_COLUMNS[7],"N° Package":EXPECTED_COLUMNS[8],
    "Code magasin":EXPECTED_COLUMNS[9],"Code unité":EXPECTED_COLUMNS[10],"Créé par":EXPECTED_COLUMNS[11],
    "Quantité":EXPECTED_COLUMNS[12],"Quantite en sac":EXPECTED_COLUMNS[13],"Quantité facturée":EXPECTED_COLUMNS[14],
    "Quantité restante":EXPECTED_COLUMNS[15],"Quantité réservée":EXPECTED_COLUMNS[16],"Ecriture lettrage":EXPECTED_COLUMNS[17],
    "Montant vente (réel)":EXPECTED_COLUMNS[18],"Coût total (réel)":EXPECTED_COLUMNS[19],"Coût total (non incorp.)":EXPECTED_COLUMNS[20],
    "Ouvert":EXPECTED_COLUMNS[21],"Type de commande":EXPECTED_COLUMNS[22],"Créé à":EXPECTED_COLUMNS[23],
    "N° séquence":EXPECTED_COLUMNS[24],"KOR par Réception":EXPECTED_COLUMNS[25],"KOR INPUT":EXPECTED_COLUMNS[26]

}

# Définition des variables
#DIRECTORY_PATH = "/opt/airflow/dags/shares"  # Remplacez par votre chemin
DIRECTORY_PATH = "/opt/airflow/files"  # Remplacez par votre chemin
ALLOWED_TYPES = [".csv"]  # Types de fichiers acceptés
ENCODINGS = ["utf-8", "ISO-8859-1", "Windows-1252"]  # Liste des encodages possibles

LOG_DIR="logs"
ERROR_FILENAME="error_date_execution.txt"
SUCCESS_FILENAME="success_date_execution.txt"

IN_DIR="in"
OUT_DIR="out"
#DATABASE_URL = "mysql+pymysql://root:root225@host.docker.internal:3306/testimportdb"

os.makedirs(DIRECTORY_PATH, exist_ok=True)


from airflow.providers.mysql.hooks.mysql import MySqlHook


def import_temp_ecc_to_ecc():
    try:
        # Initialiser le hook MySQL
        mysql_hook = MySqlHook(mysql_conn_id='mysql_conn')
        select_query = """ SELECT * FROM temp_ecc; """

        records = mysql_hook.get_records(select_query)
          # Préparer les données pour l'insertion ou la mise à jour
        data_to_insert = [
            (
                f"{record[3]}{record[4]}",  # Concaténer `N° sequence` et `N°document` pour créer `id`
                f"{record[0].strftime('%Y-%m-%d')}", f"{record[1]}",f"{record[2]}",
                f"{record[3]}",f"{record[4]}",f"{record[5]}",f"{record[6]}",
                f"{record[7]}",f"{record[8]}",f"{record[9]}",f"{record[10]}",
                f"{record[11]}",f"{record[12]}",f"{record[13]}",f"{record[14]}",
                f"{record[15]}",f"{record[16]}",f"{record[17]}",f"{record[18]}",
                f"{record[19]}",f"{record[20]}",f"{record[21]}",f"{record[22]}",
                f"{record[23].strftime('%Y-%m-%d %H:%M')}",f"{record[24]}",f"{record[25]}",f"{record[26]}",
            )
            for record in records
        ]


        delete_query = """
            DELETE FROM ecc WHERE id IN (%s)
        """ % ", ".join(["%s"] * len(data_to_insert))

        mysql_hook.run(delete_query, parameters=[row[0] for row in data_to_insert])  # Supprime les anciens enregistrements

        # Insère les nouvelles données
        mysql_hook.insert_rows(
            table="ecc",
            rows=data_to_insert,
            target_fields=["id", "accounting_date", "lot_number", "type_ecriture", "document_number", "sequence_number"]
        )
        return 'end'
    except Exception as e:
        print(f"❌ Erreur lors de l'importation des données : {e}")
        



def move_file_to_out(file_path, out_directory,statusMove:bool=True):
    """Déplace le fichier traité vers le dossier OUT en ajoutant la date et l'heure au nom du fichier."""
    try:
        # Vérifier si le dossier OUT existe, sinon le créer
        if not os.path.exists(out_directory):
            os.makedirs(out_directory)

        # Récupérer le nom du fichier et son extension
        file_name, file_extension = os.path.splitext(os.path.basename(file_path))

        # Obtenir la date et l'heure actuelles au format souhaité
        current_datetime = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Créer le nouveau nom de fichier en y ajoutant la date et l'heure
        file_name = f"{file_name}_{current_datetime}{file_extension}"
        if statusMove:
            # Définir le chemin de destination
            destination_path = os.path.join(f"{out_directory}/success", file_name)
        else:
            destination_path = os.path.join(f"{out_directory}/error", file_name)


        # Déplacer le fichier
        shutil.move(file_path, destination_path)

        # Message de succès
        suc_message = f"✅ Fichier déplacé vers {destination_path}"
        print(suc_message)
        # Appeler la fonction log_message si elle est définie
        log_message(LOG_DIR,SUCCESS_FILENAME, suc_message)

    except Exception as e:
        # Gérer les exceptions et afficher un message d'erreur
        err_message = f"❌ Erreur lors du déplacement du fichier : {e}"
        print(err_message)
        log_message(LOG_DIR,ERROR_FILENAME, err_message)



def renamed_panda_colonnes(pandasFile: pd.DataFrame,expected_columns:any,renamed_columns:object) -> pd.DataFrame:
    if not isinstance(pandasFile, pd.DataFrame):
        print("❌ Erreur : L'entrée doit être un DataFrame pandas.")
        return None
    print(f"expected_columns20202 : {expected_columns}")
    print(f"renamed_columns2022 : {renamed_columns}")
    pandasFile.rename(columns=renamed_columns, inplace=True)
    missing_columns = set(expected_columns) - set(pandasFile.columns)
    if missing_columns:
        print(f"❌ Colonnes manquantes : {', '.join(missing_columns)}")
        print(f"❌ BORISColonnes trouvees : {', '.join(pandasFile.columns)}")
        return None
    return pandasFile

def log_message(fpath,filename, message):
    """Écrit un message dans un fichier log."""
    file_path = os.path.join(f'{DIRECTORY_PATH}/{fpath}', filename)  # Chemin du fichier dans logs/
    with open(file_path, "a", encoding="utf-8") as log_file:
        log_file.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {message}\n")


# Fonction pour vérifier l'existence du répertoire
def check_directory(directory_path):
    if os.path.isdir(directory_path):
        return "check_file_in_directory"
    else:
        return "end"

# Fonction pour vérifier l'existence d'un type de fichier spécifique
def check_file_in_directory(directory_path,allow_types):
    print('ca marche',directory_path,allow_types)
    files = [f for f in os.listdir(directory_path) if os.path.splitext(f)[1] in allow_types]
    if files:
        return "verify_file_reliability"
    else:
        log_message(LOG_DIR,ERROR_FILENAME, 'fichier csv non trouvé')
        return "end"

def read_file(file,file_path,encodings,expected_columns,renamed_columns)->pd:
    result_read_file:pd=None
    for encoding in encodings:
        try:
            df = pd.read_csv(file_path, encoding=encoding, delimiter=";")
            # 🔹 Supprimer les lignes totalement vides
            df.replace("", pd.NA).dropna(how="all")
            print(f"\n📂 Contenu du fichier ({encoding}): {file}")
            print(df.head())  # Afficher les premières lignes
            result_read_file=df
            break  # Sortir de la boucle si la lecture réussit
        except UnicodeDecodeError as e:
            err_message=f"❌ Erreur d'encodage ({encoding}) pour {file}: {e}"
            logging.error(err_message)
            log_message(LOG_DIR,ERROR_FILENAME, err_message)
        except Exception as e:
            err_message=f"⚠️ Erreur lors de la lecture de {file} avec {encoding}: {e}"
            logging.error(err_message)
            log_message(LOG_DIR,ERROR_FILENAME, err_message)
            break  # Ne pas tester d'autres encodages si une autre erreur survient
    if result_read_file is not None:
        rn=renamed_panda_colonnes(result_read_file,expected_columns,renamed_columns)  # Renommer les colonnes si possible
        return rn 
    else:
        return None  # Retourne None si aucun encodage ne fonctionne

# Paramètres de connexion MySQL (à adapter)

def test_sql_connection(pdfile,temp_table)->any:
    TABLE=temp_table
    """Teste la connexion à la base de données."""
    try:
        mysql_hook = MySqlHook(mysql_conn_id='mysql_conn')
        conn = mysql_hook.get_conn()
        cursor = conn.cursor()

        # Vérification des bases de données disponibles
        cursor.execute("SHOW DATABASES;")
        print(cursor.fetchall())

        # Conversion des dates si présentes
        if "accounting_date" in pdfile.columns:
            pdfile["accounting_date"] = pd.to_datetime(pdfile["accounting_date"], format="%d/%m/%Y").dt.strftime("%Y-%m-%d")

        if "created_at" in pdfile.columns:
            pdfile["created_at"] = pd.to_datetime(pdfile["created_at"], format="%d/%m/%Y %H:%M").dt.strftime("%Y-%m-%d %H:%M")

        # Vérification et conversion de quantity
        if "quantity" in pdfile.columns:
            pdfile["quantity"] = pdfile["quantity"].astype(str).str.replace(",", ".").astype(float)

        if "remaining_quantity" in pdfile.columns:
            pdfile["remaining_quantity"] = pdfile["remaining_quantity"].astype(str).str.replace(",", ".").astype(float)

        if "quantity_reserved" in pdfile.columns:
            pdfile["quantity_reserved"] = pdfile["quantity_reserved"].astype(str).str.replace(",", ".").astype(float)

        if "lettering_writing" in pdfile.columns:
            pdfile["lettering_writing"] = pdfile["lettering_writing"].astype(str).str.replace(",", ".").astype(float)

        if "sales_amount_actual" in pdfile.columns:
            pdfile["sales_amount_actual"] = pdfile["sales_amount_actual"].astype(str).str.replace(",", ".").astype(float)

        if "total_cost_actual" in pdfile.columns:
            pdfile["total_cost_actual"] = pdfile["total_cost_actual"].astype(str).str.replace(",", ".").astype(float)

        if "total_cost_not_included" in pdfile.columns:
            pdfile["total_cost_not_included"] = pdfile["total_cost_not_included"].astype(str).str.replace(",", ".").astype(float)

        if "kor_by_reception" in pdfile.columns:
            pdfile["kor_by_reception"] = pdfile["kor_by_reception"].astype(str).str.replace(",", ".").astype(float)

        if "kor_input" in pdfile.columns:
            pdfile["kor_input"] = pdfile["kor_input"].astype(str).str.replace(",", ".").astype(float)

        # Remplacement des NaN par ''
        pdfile = pdfile.where(pdfile.notna(), '')

        print("⚠️ Données avant insertion :", pdfile.dtypes)
        print("Aperçu des données :", pdfile.head())

        # Suppression des anciennes données
        delete_query = f"DELETE FROM {TABLE};"
        cursor.execute(delete_query)
        conn.commit()
        print("⚠️ Données supprimées avant insertion.")

        # Conversion en tuples pour l'insertion
        rows_to_insert = [tuple(row) for row in pdfile.itertuples(index=False)]
        #print('📌 Données à insérer :', rows_to_insert)

        # Insertion des données
        mysql_hook.insert_rows(table=TABLE, rows=rows_to_insert)
        print("✅ Insertion réussie !")

    except Exception as e:
        error_msg = f"❌ Erreur de connexion : {e}"
        print(error_msg)
        log_message(LOG_DIR, ERROR_FILENAME, error_msg)


def check_file_reliability_from_pandas(pdf:pd,expected_columns:any,column_types:any)->bool:
    result_check=True
    try:
        # Vérifier si toutes les colonnes attendues sont présentes
        missing_columns = [col for col in expected_columns if col not in pdf.columns]
        
        if missing_columns:
            print(f"Taille de EXPECTED_COLUMNS: {len(EXPECTED_COLUMNS)}")
            print(f"Contenu de EXPECTED_COLUMNS: {EXPECTED_COLUMNS}")

            #Ecrire dans le log
            raise ValueError(f"Colonnes manquantes: {', '.join(missing_columns)}")
        # Vérifier les types de données des colonnes
        for column, expected_type in column_types.items():
            if column in pdf.columns:
                for idx, value in enumerate(pdf[column]):
                    try:
                        # Vérification Date
                        if expected_type == date:
                            value = pd.to_datetime(value, format="%d/%m/%Y").date()  

                        # Vérification DateTime
                        elif expected_type == datetime:
                            value = pd.to_datetime(value, format="%d/%m/%Y %H:%M")  

                        # Vérification Integer
                        elif expected_type == int:
                            try:
                                value = int(value)
                            except ValueError:
                                error_msg = f"❌ Erreur Ligne {idx} : {column} - {value} -> Type attendu : {expected_type.__name__}"
                                print(error_msg)
                                log_message(LOG_DIR, ERROR_FILENAME, error_msg)
                                return False

                        # Vérification Float
                        elif expected_type == float:
                            if isinstance(value, str):  
                                value = value.replace(",", ".")  
                            value = float(value)  # Convertir en float
                            success_msg = f"✅ Ligne {idx} : {column} - {value} -> Type correct (float)"

                        # Vérification String
                        elif expected_type == str:
                            if not isinstance(value, str) and not pd.isna(value) and value != "":
                                error_msg = f"❌ Erreur Ligne {idx} : {column} - {value} -> Type attendu : {expected_type.__name__}"
                                print(error_msg)
                                log_message(LOG_DIR, ERROR_FILENAME, error_msg)
                                return False

                        else:
                            error_msg = f"❌ Erreur Ligne {idx} : {column} - {value} -> Type inconnu ({expected_type})"
                            print(error_msg)
                            log_message(LOG_DIR, ERROR_FILENAME, error_msg)
                            result_check = False

                    except (ValueError, TypeError):
                        result_check = False
                        error_msg = f"❌ Erreur Ligne {idx} : {column} - {value} -> Type attendu : {expected_type.__name__}"
                        print(error_msg)
                        log_message(LOG_DIR, ERROR_FILENAME, error_msg)

                error_msg=("✅ Le fichier respecte les colonnes attendues et les types de données.",result_check)
                row_count = len(pdf)
                print('✅Lignes ',error_msg,row_count)
                log_message(LOG_DIR,"statut_date_execution.txt", error_msg)
                return result_check

        error_msg=("✅ Le fichier respecte les colonnes attendues et les types de données.",result_check)
        row_count = len(pdf)
        print('✅Lignes ',error_msg,row_count)
        log_message(LOG_DIR,"statut_date_execution.txt", error_msg)
        return result_check

    except Exception as e:
        error_msg=(f"❌ Erreur de fiabilité : {str(e)}")
        print(error_msg)
        log_message(LOG_DIR,ERROR_FILENAME, error_msg)
        return False


# Définir la tâche de vérification de fiabilité du fichier
def verify_file_reliability(directory_path,allow_types,encodings,expected_columns,column_types,renamed_columns):
    print('camarche22',directory_path,allow_types,encodings,column_types,renamed_columns)
    files = [f for f in os.listdir(directory_path) if os.path.splitext(f)[1] in allow_types]
    for file in files:
        file_path = os.path.join(directory_path, file)
        pdFile= read_file(file,file_path,encodings,expected_columns,renamed_columns)
        if pdFile is not None:
            # ✅ Remplacer `NaN` par `None`
            if check_file_reliability_from_pandas(pdFile,expected_columns,column_types):
                print('merci')
                cursor=test_sql_connection(pdFile,"temp_ecc")
                if not cursor:
                    error_msg='connexion sql echoue'
                    print(error_msg)
                    destination_out_path=f"{DIRECTORY_PATH}/{OUT_DIR}"
                    log_message(LOG_DIR,ERROR_FILENAME,error_msg)
                    move_file_to_out(file_path,destination_out_path,False)
                else:
                    destination_out_path=f"{DIRECTORY_PATH}/{OUT_DIR}"
                    print('connexion sql reussie',cursor)
                    move_file_to_out(file_path,destination_out_path)
                    return 'import_temp_ecc_to_ecc'
            else:
                print('Merde')
                error_msg='Erreur sur la retour fichier pandas'
                log_message(LOG_DIR,ERROR_FILENAME, error_msg)
                return 'end'
        else:
            #Ecrire dans le log
            error_msg=f'{file_path} non traité Boris :{pdFile}'
            print(file_path,file,error_msg)
            #log_message(ERROR_FILENAME, error_msg)
            log_message(LOG_DIR,ERROR_FILENAME, error_msg)

            return 




default_args = {
    "owner": "airflow",
    "start_date": datetime(2025, 2, 7),
    'retry_delay': timedelta(seconds=30),
    'retries': 1,
    'retry_delay': timedelta(days=1),

}

with DAG("IMPORTATION_ECRITURE_COMPTABLES_ARTICLE_dag", default_args=default_args, 
            tags=['boris', 'bahi'],
            #schedule_interval=None
            schedule=timedelta(seconds=60),  # Nouveau paramètre
            start_date=datetime(2025, 2, 10),  # Date de début du DAG
            catchup=False,  # Empêche l'exécution rétroactive des tâches
            ) as dag:

    # Première tâche : vérifier si le répertoire existe
    check_directory_task = BranchPythonOperator(
        task_id="check_directory",
        python_callable=check_directory,
        op_kwargs={'directory_path':DIRECTORY_PATH},  # Remplacer par votre chemin
    )

    # Deuxième tâche : vérifier l'existence d'un type de fichier spécifique
    check_file_task = BranchPythonOperator(
        task_id="check_file_in_directory",
        python_callable=check_file_in_directory,
        op_kwargs={'directory_path':f'{DIRECTORY_PATH}/{IN_DIR}','allow_types':ALLOWED_TYPES}

    )

     # Deuxième tâche : vérifier l'existence d'un type de fichier spécifique
   
    """
   # Tâche 3: Lire chaque fichier si trouvé
    read_files_task = BranchPythonOperator(
        task_id="read_files",
        python_callable=read_files
    )"""

    verify_file_reliability_task = BranchPythonOperator(
    task_id='verify_file_reliability',
    python_callable=verify_file_reliability,
    op_kwargs={'directory_path':f'{DIRECTORY_PATH}/{IN_DIR}','allow_types':ALLOWED_TYPES,
               'encodings':ENCODINGS,'expected_columns':EXPECTED_COLUMNS,
               'column_types':COLUMN_TYPES,'renamed_columns':RENAMED_COLUMNS}
)
    
    import_temp_ecc_to_ecc_task = BranchPythonOperator(
        task_id="import_temp_ecc_to_ecc",
        python_callable=import_temp_ecc_to_ecc,
    )

    # Tâche de fin si aucun fichier valide ou répertoire inexistant
    end_task = EmptyOperator(task_id="end")

   # Définition des dépendances
    #check_directory_task >> check_file_task >> read_files_task >> verify_file_reliability_task >> end_task
    check_directory_task >> check_file_task >> verify_file_reliability_task >> import_temp_ecc_to_ecc_task >> end_task

    # Si le répertoire n'existe pas, on termine directement
    check_directory_task >> end_task
    # Si aucun fichier n'est trouvé, on termine directement
    check_file_task >> end_task
    
    #read_files_task >> end_task

    # Si la vérification des fichiers échoue, on termine directement
    verify_file_reliability_task >> end_task
     # Si la vérification des fichiers échoue, on termine directement
    import_temp_ecc_to_ecc_task >> end_task