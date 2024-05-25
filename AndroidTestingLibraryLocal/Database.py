"""
Database.py

Contains classes which allow for the storage of events, screenshots, and user interface heiarchies
into databases. These elements could be collected and stored as a DatabaseElement object, so that
storage and retrieval are more streamlines. Each instance of the Database class should correspond
to one instance of the TestingStrategy class.

Keep in mind that this is a template file and can be completely changed, deleted, or whatever based
on the needs of the backend team.
"""
import sqlite3
import os
import random

from typing import Optional, List, Tuple, Set
from sqlite3 import Error
from .DatabaseElement import * 
from sys import platform
from random import sample
class Database:
    
    def __init__(self):
        connection = self.__create_connection()
        self.__c = connection.cursor()

        # This datatable stores recorded events
        try:
            self.__c.execute('''CREATE TABLE IF NOT EXISTS record_event_datatable(packageName TEXT, timestamp TEXT, action TEXT, propOne TEXT, propTwo TEXT, propThree TEXT, propFour TEXT, propFive TEXT) ''')
        except sqlite3.Error as e:
            print(e)
        # This datatable stored mined event tuples
        try:
            self.__c.execute('''CREATE TABLE IF NOT EXISTS mine_datatable(packageName TEXT, activity TEXT, window TEXT, guiComponent TEXT, action TEXT, componentClass TEXT)''' )
        except sqlite3.Error as e:
            print(e)
        # This datatable stores screenshots of tested applications
        try:
            self.__c.execute('''CREATE TABLE IF NOT EXISTS validate_datatable(packageName TEXT, screenImage BLOB, testScenario TEXT)''' )
        except sqlite3.Error as e:
            print(e)
        # This datatable stores a string representation of an event tuple along with its sequence number and the order it is in the sequence.
        try:
            self.__c.execute('''CREATE TABLE IF NOT EXISTS mine_token_datatable(packageName TEXT, token TEXT, sequence INTEGER, step INTEGER)''')
        except sqlite3.Error as e:
            print(e)
        # This datatable stores the total number of sequences stored for the given android package. 
        try:
            self.__c.execute('''CREATE TABLE IF NOT EXISTS mine_manifest_datatable(packageName TEXT, numberOfSequences INTEGER)''')
        except sqlite3.Error as e:
            print(e)

    """
    Creates a connection to the database to allow us to perform store, delete, and get commands on specific datatables.
    """
    def __create_connection(self):
        conn = None
        path = os.path.join(self.__get_path())
        try:
            conn = sqlite3.connect(path)
        except Error as e:
            print(e)
        
        return conn
    
    """
    Stores a passed element in the database in one of three tables, depending on which stage the testing strategy 
    is in.
    """
    def store_element(self, element: DatabaseElement) -> None: # The element parameter is of type DatabaseElement
        connection = self.__create_connection()
        cur = connection.cursor()
              
        cur.execute(element.get_sql_store(), element.get_data())
        connection.commit()

        cur.close()
        connection.close()

    """
    Returns the data associated with the package name and MonkeyLab stage passed as parameters.
    """
    def get_table_data(self, package_name: str, monkey_lab_stage: str) -> List[Tuple]:
        connection = self.__create_connection()
        cur = connection.cursor()
        
        if(monkey_lab_stage == 'MINE'):  
            sql = '''SELECT * FROM mine_datatable WHERE packageName=?'''
        elif(monkey_lab_stage == 'VALIDATE'):
            sql = '''SELECT * FROM validate_datatable WHERE packageName=?'''
        elif(monkey_lab_stage == 'RECORD_EVENT'):
            sql = '''SELECT * FROM record_event_datatable WHERE packageName=?'''
        elif(monkey_lab_stage == 'MINE_TOKEN'):
            sql = '''SELECT * FROM mine_token_datatable WHERE packageName=?'''
        elif(monkey_lab_stage == 'MINE_MANIFEST'):
            sql = '''SELECT * FROM mine_manifest_datatable WHERE packageName=?'''
        else:
            print('Invalid Monkey Lab Stage!')
            return
        
        cur.execute(sql, (package_name,))
        records = cur.fetchall()

        cur.close()
        connection.close()

        return records

    """
    Deletes an element from the Database with the given index. If no index is
    provided, then delete the most recently stored element.
    """
    def clear_table_data(self, package_name: str, element: DatabaseElement) -> None:
        connection = self.__create_connection()
        cur = connection.cursor()

        sql = element.get_sql_delete()
        cur.execute(sql,(package_name,))
        connection.commit()
        cur.close()
        connection.close()
        
    """
    Returns the absolute file path for the Android_Testing_Library_Database.
    """
    def __get_path(self) -> str:
        dir_path = os.path.dirname(os.path.abspath(__file__))
        storage_path = os.sep.join([dir_path, "storage"])
        
        if(not os.path.isdir(storage_path)): # Checks to see if the storage folder has been created. 
            os.mkdir(storage_path)
        
        db_path = os.sep.join([storage_path, "Android_Testing_Library_Database"])
        return db_path
        
    
    """
    Drops all of the datatables from the Android_Testing_Library_Database. 
    """
    def destroyDatabase(self) -> None:
        connection = self.__create_connection()
        cur = connection.cursor()
              
        cur.execute("""DROP TABLE record_event_datatable""")
        connection.commit()

        cur.execute("""DROP TABLE mine_datatable""")
        connection.commit()

        cur.execute("""DROP TABLE validate_datatable""")
        connection.commit()

        cur.execute("""DROP TABLE mine_token_datatable""")
        connection.commit()

        cur.execute("""DROP TABLE mine_manifest_datatable""")
        connection.commit()

        cur.close()
        connection.close()
        
    
    """
    This method takes in a sequence of tokens as input and stores the tokens into the database. 
    parse_sequence_to_tokens() is called and will parse through the list of tokens and add each element into the database.
    """
    def add_token_sequence(self, sequence: List[str], package_name: str) -> None:

        # don't allow an empty sequence to be added
        if len(sequence) == 0:
            return

        index = 0     
        try: 
            sequence_number = self.get_number_sequences(package_name)
        except:
            mine_manifest_el = MineManifestDatabaseElement(package_name,0)
            self.store_element(mine_manifest_el)
            sequence_number = 0

        for token in sequence:
            self.__parse_tokens(token, package_name, index, sequence_number+1)
            index = index+1
        self.__increment_sequence(package_name, sequence_number+1)
        

    """
    Parses the event tokens so that we can insert the event tokens into the database. 
    """    
    def __parse_tokens(self, token: str, package_name: str, index: int, sequence_number: int) -> None:
        token_el = MineTokenDatabaseElement(package_name, token, sequence_number, index)
        self.store_element(token_el)

        
    """
    This method returns the number of sequences a specific app has generated.
    """
    def get_number_sequences(self, package_name: str) -> int:
        package_data = self.get_table_data(package_name,"MINE_MANIFEST")

        if(len(package_data) == 0):
            raise ValueError("The package name does not exists in the mine manifest table.")

        number = package_data[0][1]
        return number
        
    """
    Create a method in the database class that, given a specified package name and number of tokens,
    returns a list of random sequences containing the specified number of tokens. 
    The method will randomly select sequences from the database until the total number of 
    tokens from all selected sequences meets or exceeds the number of tokens requested.
    In addition, it will continue to select sequences until there are no more sequences to select. 
    If that is the case, it will return all selected sequences.

    """
    def get_token_sequences(self, num_tokens: int, package_name: str) -> List[List[str]]:
        event_tokens = [] # Initialize a list that will store lists of event tokens
        number_of_tokens = 0 # Initialize the number of tokens selected

        # make sure that the package exists; if it doesn't, then return an empty list
        try:
            number_of_sequences = self.get_number_sequences(package_name) # Gets the number of sequences for a given package name
        except ValueError:
            return []
        
        # randomly iterate through the sequence numbers
        for sequence_number in sample(range(1, number_of_sequences + 1), number_of_sequences):

            # get the sequence; ignore if it is empty
            sequence = self.__get_sequence(package_name, sequence_number)
            if len(sequence) == 0:
                continue

            # If the total number of tokens won't exceed num_tokens, then simply append the
            # sequence; else, append a truncated version of the sequnce such that the total number
            # of tokens won't exceed num_tokens and then break out of the loop.
            number_of_tokens += len(sequence)
            if number_of_tokens <= num_tokens:
                event_tokens.append(sequence)
            else:
                amount_to_truncate = number_of_tokens - num_tokens
                event_tokens.append(sequence[:-amount_to_truncate])
                break
            
        return event_tokens

    """ 
    This method increments the number of sequences for an app.

    """
    def __increment_sequence(self, package_name: str, sequence_number: int) -> None:
        connection = self.__create_connection()
        cur = connection.cursor()
              
        cur.execute("""UPDATE mine_manifest_datatable SET numberOfSequences = ? WHERE packageName = ? """, [sequence_number, package_name])
        connection.commit()

        cur.close()
        connection.close()

    """
    Retrieves all of the event tokens for a given package name and sequence number. This method returns
    a list of event tokens. 
    
    """
    def __get_sequence(self, package_name: str, sequence_number: int) -> List[str]:
        connection = self.__create_connection()
        cur = connection.cursor()
              
        cur.execute("""SELECT * FROM mine_token_datatable WHERE packageName = ? AND sequence = ?""", [package_name, sequence_number])
        connection.commit()

        recorded_tokens = cur.fetchall()

        tokens = []
        for record in recorded_tokens:
            tokens.append(record[1])
        
        cur.close()
        connection.close()
        return tokens