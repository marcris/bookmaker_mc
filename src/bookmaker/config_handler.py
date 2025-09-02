# config_handler.py

import configparser
import os

class ConfigHandler:
    def __init__(self, filename):
        self.filename = filename
        self.config = configparser.ConfigParser()
        if os.path.exists(self.filename):
            try:
                self.config.read(self.filename)
                for s in dict(self.config.sections()):
                    


                    self.project = self.config['project']
                    self.pdf = self.config['pdf']

            except configparser.Error as e:
                print(f"Error reading configuration file: {e}")


if __name__ == '__main__':
    config_handler = ConfigHandler('/home/chris/PDM-projects/BookMaker_mc/src/bookmaker/config.ini')
    print('Config sections: ', config_handler.config.sections())
    pdf_title = config_handler.config['pdf']['title']
    print(f'PDF title is {pdf_title}')
    print(f'PDF title is {config_handler.pdf['title']}')
