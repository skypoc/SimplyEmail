# !/usr/bin/env python

# Class will have the following properties:
# 1) name / description
# 2) main name called "ClassName"
# 3) execute function (calls everthing it neeeds)
# 4) places the findings into a queue
import re
import requests
import urlparse
import os
import configparser
import requests
import time
from subprocess import Popen, PIPE
from Helpers import helpers
from Helpers import Parser
from bs4 import BeautifulSoup
from cStringIO import StringIO

# import for "'ascii' codec can't decode byte" error
import sys
reload(sys)
sys.setdefaultencoding("utf-8")
# import for "'ascii' codec can't decode byte" error

class ClassName:
    def __init__(self, Domain, verbose=False):
        self.name = "Exalead XLSX Search for Emails"
        self.description = "Uses Exalead Dorking to search XLSXs for emails"
        config = configparser.ConfigParser()
        try:
            config.read('Common/SimplyEmail.ini')
            self.Domain = Domain
            self.Quanity = int(config['ExaleadXLSXSearch']['StartQuantity'])
            self.UserAgent = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}
            self.Limit = int(config['ExaleadXLSXSearch']['QueryLimit'])
            self.Counter = int(config['ExaleadXLSXSearch']['QueryStart'])
            self.verbose = verbose
            self.urlList = []
            self.Text = ""
        except:
            print helpers.color("[*] Major Settings for ExaleadXLSXSearch are missing, EXITING!\n", warning=True)

    def execute(self):
        self.search()
        FinalOutput, HtmlResults = self.get_emails()
        return FinalOutput, HtmlResults

    def convert_Xlsx_to_Csv(self, path):
        # Using the Xlsx2csv tool seemed easy and was in python anyhow
        # it also supported custom delim :)
        cmd = ['xlsx2csv', path]
        p = Popen(cmd, stdout=PIPE)
        stdout, stderr = p.communicate()
        return stdout.decode('ascii', 'ignore')

    def download_file(self, url):
        local_filename = url.split('/')[-1]
        # NOTE the stream=True parameter
        r = requests.get(url, stream=True)
        with open(local_filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=1024):
                if chunk:  # filter out keep-alive new chunks
                    f.write(chunk)
                    # f.flush() commented by recommendation from J.F.Sebastian
        return local_filename

    def search(self):
        while self.Counter <= self.Limit:
            time.sleep(1)
            if self.verbose:
                p = '[*] Exalead XLSX Search on page: ' + str(self.Counter)
                print helpers.color(p, firewall=True)
            try:
                url = 'http://www.exalead.com/search/web/results/?q="%40' + self.Domain + \
                      '"+filetype:xlsx&elements_per_page=' + str(self.Quanity) + '&start_index=' + str(self.Counter)
            except Exception as e:
                error = "[!] Major issue with Exalead XLSX Search:" + str(e)
                print helpers.color(error, warning=True)
            try:
                r = requests.get(url, headers=self.UserAgent)
            except Exception as e:
                error = "[!] Fail during Request to Exalead (Check Connection):" + str(e)
                print helpers.color(error, warning=True)
            try:
                RawHtml = r.content
                self.Text += RawHtml  # sometimes url is broken but exalead search results contain e-mail
                soup = BeautifulSoup(RawHtml)
                self.urlList = [h4.a["href"] for h4 in soup.findAll('h4', class_='media-heading')]
            except Exception as e:
                error = "[!] Fail during parsing result: " + str(e)
                print helpers.color(error, warning=True)
            self.Counter += 30

        # now download the required files
        try:
            for url in self.urlList:
                if self.verbose:
                    p = '[*] Exalead XLSX search downloading: ' + str(url)
                    print helpers.color(p, firewall=True)
                try:
                    FileName = self.download_file(url)
                    self.Text += self.convert_Xlsx_to_Csv(FileName)
                except Exception as e:
                    error = "[!] Issue with opening Xlsx Files:%s\n" % (str(e))
                    print helpers.color(error, warning=True)
                try:
                    os.remove(FileName)
                except Exception as e:
                    print e
        except:
            print helpers.color("[*] No XLSX's to download from Exalead!\n", firewall=True)

        if self.verbose:
            p = '[*] Searching XLSX from Exalead Complete'
            print helpers.color(p, status=True)

    def get_emails(self):
        Parse = Parser.Parser(self.Text)
        Parse.genericClean()
        Parse.urlClean()
        FinalOutput = Parse.GrepFindEmails()
        HtmlResults = Parse.BuildResults(FinalOutput, self.name)
        return FinalOutput, HtmlResults
