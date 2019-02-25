import psycopg2 as pg
import pandas as pd

class PG_Interactor(object):
    def __init__(self, DBname, Username, Password, HostIP, Port):
        self.DBname = DBname
        self.Username = Username
        self.Password = Password
        self.HostIP = HostIP
        self.Port = Port
        self.cursor = None

    def make_cursor(self):
        connection = pg.connect(database=self.DBname, user=self.Username, password=self.Password, host=self.HostIP, port=self.Port)
        self.cursor = connection.cursor()

    def execute_sql(self, sqlcode):
        self.cursor.execute(sqlcode)
        result = self.cursor.fetchall()
        return result

    # get_intersection_ID via intersection name
    def get_intersection_ID(self, intersection_name):
        result = self.execute_sql('SELECT * FROM tbl_cross WHERE name=\'{}\''.format(intersection_name))
        return result[0][0]
    
    def get_roads_info(self, intersection_ID):
        result = self.execute_sql('SELECT * FROM tbl_road WHERE crossid=\'{}\''.format(intersection_ID))
        colnames = self.execute_sql('SELECT column_name FROM information_schema.columns \
                                WHERE table_schema=\'public\' and table_name=\'tbl_road\'')
        colnames = [x[0] for x in colnames]
        result = pd.DataFrame(result)
        result.columns = colnames
        return result
    
    def get_entrances_info(self, roads_ID):
        """
        roads_ID is target intersection's all roadsID
        """
        result = []
        for road_ID in roads_ID:
            row = self.execute_sql('SELECT * FROM tbl_entrance WHERE roadid=\'{}\''.format(road_ID))
            result.append(row[0])
        colnames = self.execute_sql('SELECT column_name FROM information_schema.columns \
                                WHERE table_schema=\'public\' and table_name=\'tbl_entrance\'')
        colnames = [x[0] for x in colnames]
        result = pd.DataFrame(result)
        result.columns = colnames
        return result

    def get_lanes_info(self, entrances_ID):
        """
        entrances_ID is target intersection's all roads' entrances' ID
        """
        result = []
        for enID in entrances_ID:
            rows = self.execute_sql('SELECT * FROM tbl_lane WHERE sourceid=\'{}\''.format(enID))
            for row in rows:
                result.append(row)
        colnames = self.execute_sql('SELECT column_name FROM information_schema.columns \
                                WHERE table_schema=\'public\' and table_name=\'tbl_lane\'')
        colnames = [x[0] for x in colnames]
        result = pd.DataFrame(result)
        result.columns = colnames
        return result



MyInteractor = PG_Interactor('GISDB', 'postgres', '123456', '10.10.201.5', '54324')
MyInteractor.make_cursor()
#tbl_cross = MyInteractor.execute_sql('SELECT * FROM tbl_cross LIMIT 10')
# get intersection table:
tbl_cross = MyInteractor.execute_sql('SELECT * FROM tbl_cross')
colnames = MyInteractor.execute_sql('SELECT column_name FROM information_schema.columns \
                                WHERE table_schema=\'public\' and table_name=\'tbl_cross\'')
tbl_cross = pd.DataFrame(tbl_cross)
tbl_cross.columns = [x[0] for x in colnames]
# get target_intersection ID
target_interID = MyInteractor.get_intersection_ID('王宇清的测试路口')
# get target_intersection's road table:
roadsInfo = MyInteractor.get_roads_info(target_interID)
# get target_intersection's each road'entrance information:
entranceInfo = MyInteractor.get_entrances_info(roadsInfo['id'])
# get target_intersection's each entrae's lane information:
laneInfo = MyInteractor.get_lanes_info(entranceInfo['id'])