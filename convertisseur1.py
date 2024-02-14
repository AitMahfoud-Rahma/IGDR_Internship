#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse
import pandas as pd
from unidecode import unidecode
from fuzzywuzzy import fuzz
import logging
import datetime

def install_packages():
    try:
        import subprocess
        subprocess.run(["pip", "install", "fuzzywuzzy", "unidecode", "pandas", "Levenshtein", "logging"], check=True)
        print("Les packages ont été installés avec succès.")
    except Exception as e:
        print(f"Une erreur s'est produite lors de l'installation des packages : {str(e)}")

def check_dog_existence(file_jotform, file_db, log_messages, logger):
    for i, nom_usuel in enumerate(file_jotform['Nom Usuel (animal)']):
        # Récupérer les informations du chien dans le formulaire JotForm
        date_naissance_jotform = file_jotform['Date de naissance'][i]
        puce_jotform = file_jotform['Puce'][i]
        # Filtrer la base de données pour le nom usuel correspondant
        matching_rows = file_db[(file_db['Nom usuel'] == nom_usuel) & (file_db['Date de naissance'] == date_naissance_jotform) & (file_db['Puce'] == puce_jotform)]

        # Vérifier l'existence du chien dans la base de données
        if not matching_rows.empty:
            for index, row in matching_rows.iterrows():
                # Comparer la date de naissance et la puce
                date_naissance_db = row['Date de naissance']

                # Vérifier la similarité des noms
                check_existence_and_similarity(
                    "Le chien",
                    nom_usuel,
                    file_db['Nom usuel'],
                    log_messages,
                    logger
                )

                if date_naissance_jotform == date_naissance_db:
                    message = f"Le chien ({nom_usuel}) existe déjà dans la base de données avec la même date de naissance et la même puce."
                    logger.info(message)
                else:
                    message = f"Le chien ({nom_usuel}) existe dans la base de données, mais avec une date de naissance ou une puce différente."
                    logger.warning(message)
        else:
            message = f"Le chien ({nom_usuel}) n'existe pas dans la base de données."
            logger.warning(message)

def check_existence_and_similarity(field_name, jotform_value, db_data, log_messages, logger, category, i):
    # Extracting relevant columns based on category
    db_nom_column = db_data[f'{category} - Nom'].apply(lambda x: unidecode(str(x)) if pd.notna(x) else x).str.lower()
    db_prenom_column = db_data[f'{category} - Prénom'].apply(lambda x: unidecode(str(x)) if pd.notna(x) else x).str.lower()

    # Jotform modification
    jotform_nom = file_jotform[f'Nom ({category.lower()})'][i]  # Mettez à jour en conséquence si nécessaire
    jotform_prenom = file_jotform[f'Prénom ({category.lower()})'][i]  # Mettez à jour en conséquence si nécessaire
    jotform_value_mod = unidecode(f"{jotform_nom} {jotform_prenom}").lower()

    # Separate the name and surname for log messages
    jotform_value_name = unidecode(jotform_nom).lower()
    jotform_value_surname = unidecode(jotform_prenom).lower()

    # Check existence
    exists = (jotform_value_name == db_nom_column) & (jotform_value_surname == db_prenom_column)

    if exists.any():
        message = f"{field_name} ({jotform_value}) existe déjà dans la base de données."
        logger.info(message)
        log_messages.add(message)
    else:
        # Vérifier si les noms et prénoms ne sont pas renversés
        reverse_check = ((db_nom_column == jotform_value_surname) & (db_prenom_column == jotform_value_name)) | \
                        ((db_nom_column == jotform_value_name) & (db_prenom_column == jotform_value_surname))

        if reverse_check.any():
            message_reverse = f"Attention : Les noms et prénoms pour {field_name} ({jotform_value}) semblent inversés dans la base de données."
            log_messages.add(message_reverse)
            logger.info(message_reverse)
        else:
            message = f"{field_name} ({jotform_value}) n'existe pas dans la base de données."
            logger.info(message)
            log_messages.add(message)
            
        #else:
            # # Check similarity
            # similarity_nom = db_nom_column.apply(lambda x: fuzz.ratio(x, jotform_value_mod) if isinstance(x, str) else 0)
            # similarity_prenom = db_prenom_column.apply(lambda x: fuzz.ratio(x, jotform_value_mod) if isinstance(x, str) else 0)

            # max_similarity_nom = similarity_nom.max()
            # max_similarity_prenom = similarity_prenom.max()

            # if max_similarity_nom >= 65 or max_similarity_prenom >= 65:
            #     index_exact_match_nom = similarity_nom.idxmax()
            #     index_exact_match_prenom = similarity_prenom.idxmax()

            #     value_exact_in_database_nom = db_nom_column.loc[index_exact_match_nom]
            #     value_exact_in_database_prenom = db_prenom_column.loc[index_exact_match_prenom]

            #     message = f"{field_name} ({jotform_value}) existe déjà dans la base de données avec une légère différence dans l'orthographe. " \
            #               f"Valeur exacte dans la base de données : {value_exact_in_database_nom} {value_exact_in_database_prenom}."
            #     logger.info(message)
            #     log_messages.add(message)
        # else:
        #     message = f"{field_name} ({jotform_value}) n'existe pas dans la base de données."
        #     logger.info(message)
        #     log_messages.add(message)

def main_verification(file_jotform, file_db, log_path):
    log_messages = set()
    traite_chiens = {}

    logger = logging.getLogger('VerificationLogger')
    logger.setLevel(logging.INFO)

    # Création du gestionnaire de fichiers pour écrire les logs
    file_handler = logging.FileHandler(log_path)
    file_handler.setLevel(logging.INFO)

    # Création du formateur de logs
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] - %(message)s')
    file_handler.setFormatter(formatter)

    # Ajout du gestionnaire de fichiers au logger
    logger.addHandler(file_handler)

    if 'Affixe_Original' not in file_jotform.columns:
        # Store original affix in a new temporary column
        file_jotform['Affixe_Original'] = file_jotform['Affixe']

    affixe_without_nan = file_db['Affixe'].dropna()
    unique_values = affixe_without_nan.unique()
    unique_values_mod = affixe_without_nan.apply(lambda x: unidecode(x).replace(' ', '').lower()).unique()
    file_jotform['Affixe'] = file_jotform['Affixe'].dropna().apply(lambda x: unidecode(x).replace(' ', '').lower())

    result = file_jotform['Affixe'].isin(unique_values_mod)
    for i, affixe_jotform in enumerate(file_jotform['Affixe']):
        affixe_jotform_mod = unidecode(affixe_jotform).lower().strip()
        affixe_original = file_jotform['Affixe_Original'][i]

        if affixe_jotform_mod in unique_values_mod:
            index_base_de_donnees = unique_values_mod.tolist().index(affixe_jotform_mod)
            affixe_base_de_donnees = unique_values[index_base_de_donnees]

            message = f"L'affixe : ({affixe_original}) existe déjà dans la base de données sous le nom : ({affixe_base_de_donnees})"
            logger.info(message)
        else:
            message = f"L'affixe : ({affixe_original}) n'existe pas dans la base de données."
            logger.warning(message)

        puce_jotform = file_jotform['Puce'][i]
        if pd.notna(puce_jotform):
            nombre_chiffres_puce = sum(c.isdigit() for c in str(puce_jotform))

            if nombre_chiffres_puce < 15:
                nom_usuel_correspondant = file_jotform['Nom Usuel (animal)'][i]
                message_puce = f"Une puce avec un nombre de chiffres de : {nombre_chiffres_puce} a été détectée.\n Veuillez vérifier le pays d'origine de l'animal avec la Puce : {puce_jotform}. Nom Usuel correspondant : {nom_usuel_correspondant}. Numéro de ligne dans file_jotform : {i + 1}"
                logger.warning(message_puce)

            # Vet check
        check_existence_and_similarity(
            "Le vétérinaire",
            file_jotform['Nom (vétérinaire)'][i] + ' ' + file_jotform['Prénom (vétérinaire)'][i],
            file_db,
            log_messages,
            logger,
            category="Vétérinaire",
            i=i  # Passer la valeur de 'i' à la fonction
        )

        # Proprio check
        check_existence_and_similarity(
            "Le propriétaire",
            file_jotform['Nom (propriétaire)'][i] + ' ' + file_jotform['Prénom (propriétaire)'][i],
            file_db,
            log_messages,
            logger,
            category="Propriétaire",
            i=i
        )

        # Chien check
        check_dog_existence(file_jotform, file_db, log_messages, logger)

        # Ajoutez le chien au dictionnaire une fois le traitement terminé
        traite_chiens[affixe_jotform] = True

    return log_messages

def generate_log_file():
    current_time = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_file_name = f"verification_log_{current_time}.log"
    return log_file_name

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Script de vérification")
    parser.add_argument("path_db", type=str, help="Chemin vers le fichier de base de données")
    parser.add_argument("path_jotform", type=str, help="Chemin vers le fichier JotForm")
    args = parser.parse_args()

    # Check packages installation
    install_packages()

    # Charger les fichiers à partir des chemins fournis en ligne de commande
    path_db = args.path_db
    path_jotform = args.path_jotform
    file_db = pd.read_excel(path_db, header=0)
    sheet_name = "Form Responses"
    file_jotform = pd.read_excel(path_jotform, sheet_name=sheet_name, header=0)

    # Appel de la fonction main_verification avec les fichiers d'entrée
    log_messages = main_verification(file_jotform, file_db, generate_log_file())

    with open('output_file.log', 'w') as log_file:
        for message in log_messages:
            log_file.write(message + '\n')

    print(f"Le fichier de log a été généré avec succès.")
