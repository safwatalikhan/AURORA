"""
DatabaseElement.py

Contains classes which allow for the storage of events, screenshots, and user interface heiarchies
into databases. These elements could be collected and stored as a DatabaseElement object, so that
storage and retrieval are more streamlines. Each instance of the Database class should correspond
to one instance of the TestingStrategy class.

Keep in mind that this is a template file and can be completely changed, deleted, or whatever based
on the needs of the backend team.
"""

class DatabaseElement:

    """
    The DatabaseElement class contains the subclasses RecordDatabaseElement, MineDatabaseElement, and ValidateDatabaseElement. Each subclass
    represents a phase along the MonkeyLab testing strategy. 
    """

    def __init__(self):
        pass
    """ 
    This will get the correct sql query for storing the elements in the database depending on the element type. 
    """
    def get_sql_store(self):
        pass
    """
    This will get the correct sql query for deleting the elements in the database depending on the element type. 
    """
    def get_sql_delete(self):
        pass
    """
    This will return a dictionary containing the class attributes, with keys matching the variable names. 
    """
    def get_data(self):
        pass

    def get_table_name(self):
        pass

class RecordEventDatabaseElement(DatabaseElement):  
        """Stores event information during the record phase"""
        def __init__(self,package_name,timestamp,action, prop_1, prop_2, prop_3=None, prop_4=None, prop_5=None):
            self.package_name = package_name # This is the application's package name. The package name is being used as the datatable's indice. 
            self.timestamp = timestamp # When the event was logged in the system.
            self.action = action # Action performed on device i.e tap, long tap
            self.prop_1 = prop_1 # The x-value regarding the specific action.
            self.prop_2 = prop_2 # The y-value regarding the specific action.
            self.prop_3 = prop_3 # The third property regarding a specific action. This may be the duration of a tap or the x_2 coordinate of a swipe.
            self.prop_4 = prop_4 # The fourth propery regarding a specific action. This may not be set. This property will be the y_2 coordinate of a swipe if set.
            self.prop_5 = prop_5 # The fifth property regarding a swipe action. This represents the duration of the swipe event.

        def get_sql_store(self):
            return '''INSERT INTO record_event_datatable(packageName,timestamp,action,propOne,propTwo,propThree,propFour, propFive) VALUES(?,?,?,?,?,?,?,?)'''
    
        def get_sql_delete(self):
            return '''DELETE FROM record_event_datatable WHERE packageName=?'''

        def get_data(self):
            return [self.package_name, self.timestamp,self.action,self.prop_1,self.prop_2,self.prop_3,self.prop_4,self.prop_5]   
            
class MineDatabaseElement(DatabaseElement):
    """Stored event tuples from the mine phase"""
       
    def __init__(self, package_name, activity, window, gui_component, action, component_class):
        # The tuple <activity, window, gui component, action, component class>
        self.package_name = package_name # This is the application's package name. The package name is being used as the datatable's indice. 
        self.activity = activity # This is the screen that contains the GUI components on the Android application.
        self.window = window # This is used to distinguish whether the action is being performed on the screen vs the Android Keyboard.
        self.gui_component = gui_component # This is the GUI element that is undergoing the action.
        self.action = action # This is a string representing the action taken on the current event.
        self.component_class = component_class # This is the class of object that self.gui_component is.
        
    def get_sql_store(self):
        return '''INSERT INTO mine_datatable(packageName,activity,window,guiComponent,action,componentClass) VALUES(?,?,?,?,?,?)'''

    def get_sql_delete(self):
        return '''DELETE FROM mine_datatable WHERE packageName=?'''

    def get_data(self):
        return [self.package_name, self.activity, self.window, self.gui_component, self.action, self.component_class]

class MineTokenDatabaseElement(DatabaseElement):
    """Stores event token generate from a specific event tuple"""
    def __init__(self, package_name: str, token: str, sequence: int, step: int):
        # The token <package name, token, sequence, step>
        self.package_name = package_name # This is the application's package name. The package name is being used as the datatable's indice. 
        self.token = token # Token is the string representitive of an event tuple.
        self.sequence = sequence # This is the event sequence to which the event token belongs.
        self.step = step # This is the order that this token belongs in for a specific sequence.
        
    def get_sql_store(self):
        return '''INSERT INTO mine_token_datatable(packageName,token,sequence,step) VALUES(?,?,?,?)'''

    def get_sql_delete(self):
        return '''DELETE FROM mine_token_datatable WHERE packageName=?'''

    def get_data(self):
        return [self.package_name, self.token, self.sequence, self.step]

class MineManifestDatabaseElement(DatabaseElement):
    """Stores the number of sequences that have been recorded for a given package name"""
    def __init__(self, package_name, sequence):
        self.package_name = package_name
        self.sequence = sequence
    
    def get_sql_store(self):
        return '''INSERT INTO mine_manifest_datatable(packageName, numberOfSequences) VALUES(?,?)'''

    def get_sql_delete(self):
        return '''DELETE FROM mine_manifest_datatable WHERE packageName=?'''

    def get_data(self):
        return [self.package_name, self.sequence]
    
        
class ValidateDatabaseElement(DatabaseElement):
    """Stored when executing app"""

    def __init__(self, package_name, screen_image, test_scenario):
        self.package_name = package_name # This is the application's package name. The package name is being used as the datatable's indice.
        self.screen_image = screen_image # The screenshot in PNG format.
        self.test_scenario = test_scenario # List of adb events sent to the device.

    def get_sql_store(self):
        return '''INSERT INTO validate_datatable(packageName,screenImage,testScenario) VALUES(?,?,?)'''
        
    def get_sql_delete(self):
        return '''DELETE FROM validate_datatable WHERE packageName=?'''

    def get_data(self):
        return [self.package_name, self.screen_image, self.test_scenario]