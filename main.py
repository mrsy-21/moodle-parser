import json
import re
import time
import os
import urllib
import pandas as pd
import sys
import grequests
import colors

from typing import Dict, List
from bs4 import BeautifulSoup
from bs4.element import ResultSet, Tag
from selenium import webdriver
from selenium.common import NoSuchElementException
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By


class Parser:
    """A class for parsing data from a web page."""

    headers_dict: Dict[str, str] = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Cookie': '',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'cross-site',
        'DNT': '1',
        'Sec-GPC': '1',}

    def __init__(self, login_url: str) -> None:
        """
        Constructor of the Parser class
        :param login_url: URL address web page 
        """
        self.login_url: str = login_url
        browsers: List[str] = ["Firefox", "Chrome", "Edge", "Safari"]
        self.browser: str = input("Enter name your browser(For example: Chrome, Firefox, Edge, Safari) : ").title().strip()
        if self.browser not in browsers:
            print(f"[{colors.Colors.RED}Fail{colors.Colors.RESET}] Can't get driver. Please download webdriver. Some of this: Chrome, Firefox, Edge, Safari")
            input("Press any key for exit!")
            sys.exit()
        self.driver: webdriver = self.__set_driver()
        self.courses_name: List[str] = []

    def __set_driver(self):
        """
        Sets webdriver according to default name
        Currently available browsers:
            1. Firefox
            2. Chrome
            3. Edge
            4. Safari
        """
        match self.browser:
            case "Firefox":
                driver: webdriver = webdriver.Firefox()
            case "Chrome":
                driver: webdriver = webdriver.Chrome()
            case "Edge":
                driver: webdriver = webdriver.Edge()
            case "Safari":
                driver: webdriver = webdriver.Safari()
        return driver

    def __login(self) -> None:
        """Login to a webpage."""
        try:
            self.driver.get(self.login_url)
            login_btn: WebElement = self.driver.find_element(By.CLASS_NAME, 'btn.login-identityprovider-btn.btn-block')
            login_btn.click()

            TARGET_URL: str = "https://exam.nuwm.edu.ua/"
            WebDriverWait(self.driver, 100).until(ec.url_to_be(TARGET_URL))
            # Save cookie
            session_cookie: str = f"MoodleSession={self.driver.get_cookie('MoodleSession')['value']}"
            self.headers_dict["Cookie"] = session_cookie
        except NoSuchElementException:
            print(f"[{colors.Colors.RED}Fail{colors.Colors.RESET}] Failed to find element. Check the URL or element selector.")

    def __extract_course_links(self) -> None:
        """Extract links to courses"""
        try:
            self.driver.get("https://exam.nuwm.edu.ua/my/courses.php")
            time.sleep(1)
            soup: BeautifulSoup = BeautifulSoup(self.driver.page_source, 'html.parser')
            match_value: Tag = soup.find(class_='card-body p-3')
            links: ResultSet = match_value.find_all('a', href=True)
            links_data: List[Dict[str, str]] = list(
                set([i.get("href") for i in list(set(links)) if "?id=" in i.get("href")]))
            with open('course_urls.json', 'w', encoding='utf-8') as file:
                json.dump(links_data, file, ensure_ascii=False, indent=4)
        except NoSuchElementException:
            print(f"[{colors.Colors.RED}Fail{colors.Colors.RESET}] Failed to find element. Check the URL or element selector")

    def __extract_assessment_journal(self, course_url: str) -> None:
        """
        Extract assessment journal from a course
        :param course_url: URL of the course
        """
        self.driver.get(course_url)
        WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable(
            (By.LINK_TEXT, "Журнал оцінок"))).click()

        soup: BeautifulSoup = BeautifulSoup(self.driver.page_source, 'html.parser')
        course_name: str = soup.find('h1').text
        headers: ResultSet = soup.find_all('th', class_=lambda value: value and value.startswith('header column-'))
        
        print(f"[{colors.Colors.GREEN}OK{colors.Colors.RESET}] Extract assessment journal {course_name} successful")

        headers_data: List[str] = []
        for header in headers:
            headers_data.append(header.text.strip())
        headers_str: str = ','.join(headers_data)
        headers_list: List[str] = headers_str.split(',')

        rows: ResultSet = soup.find_all('tr', class_=lambda value: value and value.startswith('cat_'))
        rows_data: List[List[str]] = []
        for row in rows:
            row_data: List[str] = [elem.text.strip() for elem in row.find_all(['th', 'td'])]
            while len(row_data) < len(headers_list):
                row_data.append('')

            if any(row_data):
                rows_data.append(row_data)

        folder_path: str = 'assessment-journal-on-courses'
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

        df = pd.DataFrame(rows_data, columns=headers_list)

        df.to_excel(f"{folder_path}/{course_name.strip().replace(' ', '-')}"
                    f"-journal.xlsx", index=False)

    def __extract_students_list(self) -> None:
        """Extract students from a course"""
        WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable(
            (By.LINK_TEXT, "Учасники"))).click()
        soup: BeautifulSoup = BeautifulSoup(self.driver.page_source, 'html.parser')
        course_name: str = soup.find('h1').text
        
        print(f"[{colors.Colors.GREEN}OK{colors.Colors.RESET}] Extract students list from {course_name} successful\n")

        students: List[List[str]] = []
        for i in range(2, 6):
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//tr[starts-with(@id, 'user-index-participants-')]")))
            soup: BeautifulSoup = BeautifulSoup(self.driver.page_source, 'html.parser')
            tr_student_rows: ResultSet = soup.find_all('tr', id=lambda
                value: value and value.startswith('user-index-participants-'))
            
            for row in tr_student_rows:
                td_data_elements: ResultSet = row.find_all('td')
                data: List[str] = [
                    element.text.strip().replace("Виберіть", "").replace("\"", "")
                    for element in td_data_elements if element.text.strip().replace("\\", "")]
                if data:
                    data[0] = ' '.join(data[0].split())
                    students.append(data) 

            try:
                next_page: WebElement = self.driver.find_element(
                    By.XPATH, f"//a[@class='page-link']/span[text()='{i}']")
                next_page.click()
                time.sleep(0.5)
            except NoSuchElementException:
                break

        folder_path: str = 'list-of-students-on-courses'
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

        with open(f'{folder_path}/{course_name.replace(' ', '-')}'
                  f'-students-list.json', 'w', encoding='utf-8') as file:
            json.dump(students, file, ensure_ascii=False, indent=4)

    def __extract_and_save_course_links(self) -> None:
        """Extract and save course links."""
        WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable(
            (By.LINK_TEXT, "Освітня компонента"))).click()

        soup: BeautifulSoup = BeautifulSoup(self.driver.page_source, 'html.parser')
        course_name: str = soup.find('h1').text
        self.courses_name.append(course_name)
        folder_path: str = 'source-links-on-course'
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

        links: ResultSet = soup.find_all('a', class_=lambda value: value and value.startswith('aalink'))
        links_dict: Dict[str, str] = {"1": f"{course_name}"}
        for link in links:
            links_dict[link.text] = link['href']
        
        with open(f"{folder_path}/{course_name.strip().replace(' ', '-')}"
                  f"-course-link.json", 'w', encoding='utf-8') as file:
            json.dump(links_dict, file, ensure_ascii=False, indent=4)

    def __download_files_from_links(self, folder_path_courses: str) -> None:
        """
        Download files from links.
        :param folder_path_courses: The path to the directory containing links to course files
        """
        print(f"[{colors.Colors.GREEN}OK{colors.Colors.RESET}] Start process download files ...")

        with grequests.Session() as session:
            session.headers.update(self.headers_dict)

            for cookie in self.driver.get_cookies():
                session.cookies.set(cookie['name'], cookie['value'])
            
            for file_name in os.listdir(folder_path_courses):
                links_dict: Dict[str, str] = {}
                if file_name.endswith('.json'):
                    with open(os.path.join(folder_path_courses, file_name), 'r', encoding='utf-8') as file:
                        data: Dict[str, str] = json.load(file)
                        links_dict.update(data)
                requests = [grequests.get(url, session=session, timeout=5) for url in links_dict.values()]

                responses = grequests.map(requests, size=6)

                folder_path: str = os.path.join("downloads_files_from_courses", links_dict.get("1", "").strip())
                if not os.path.exists(folder_path):
                    os.makedirs(folder_path)

                for link_text, response in zip(links_dict.keys(), responses):
                    if response is not None and response.ok:
                        if 'Content-Disposition' in response.headers:
                            file_name: str = response.headers['Content-Disposition'].split("filename=")[1]
                            file_name = re.sub(r'[\\/*?:"<>|]', ' ', file_name)
                            file_name = urllib.parse.unquote(file_name)
                            link_text = re.sub(r'[\\/*?:"<>|]', '-', link_text)
                            with open(os.path.join(folder_path, link_text.strip() + '.' + file_name.split('.')[-1]).strip(), 'wb') as file:
                                for chunk in response.iter_content(chunk_size=8192):
                                    if chunk:
                                        file.write(chunk)
                        elif 'folder' in response.url:
                            self.driver.get(response.url)
                            soup: BeautifulSoup = BeautifulSoup(self.driver.page_source, 'html.parser')
                            links: ResultSet = soup.find_all('a', string=lambda
                            text: text is not None and ".pdf" in text)
                            links_dict_for_folder: Dict[str, str] = {}
                            for link in links: 
                                links_dict_for_folder[link.text] = link['href']

                            for link_text_for_folder, url_for_folder in links_dict_for_folder.items():
                                response_for_folder: requests.Response = session.get(url_for_folder, stream=True, timeout=5) # type: ignore
                                if response_for_folder is not None and response_for_folder.ok:
                                    if 'Content-Disposition' in response_for_folder.headers:
                                        file_name_for_folder: str = response_for_folder.headers['Content-Disposition'].split("filename=")[1]
                                        file_name_for_folder = re.sub(r'[\\/*?:"<>|]', ' ', file_name_for_folder)
                                        file_name_for_folder = urllib.parse.unquote(file_name_for_folder)
                                        link_text_for_folder = re.sub(r'[\\/*?:"<>|]', '-',link_text_for_folder)
                                        with open(os.path.join(folder_path, link_text_for_folder.strip() + '.' + file_name_for_folder.split('.')[-1]).strip(),'wb') as file:
                                            for chunk in response_for_folder.iter_content(chunk_size=8192):
                                                if chunk:
                                                    file.write(chunk)
                    else:
                        continue
        print(f"[{colors.Colors.GREEN}OK{colors.Colors.RESET}] Files uploaded successfully")

    def run(self) -> None:
        """
        The function to execute all methods of a class
        """
        self.__login()
        self.__extract_course_links()

        with open('course_urls.json', 'r', encoding='utf-8') as file:
            list_links: List[str] = json.load(file)
        
        for link in list_links:
            self.__extract_assessment_journal(link)
            self.__extract_students_list()
            self.__extract_and_save_course_links()

        with open('courses_name.json', 'w', encoding='utf-8') as file:
            json.dump(self.courses_name, file, ensure_ascii=False, indent=4)

        self.__download_files_from_links('source-links-on-course')
        self.driver.close()
        

if __name__ == '__main__':
    parser = Parser("https://exam.nuwm.edu.ua/login/index.php")
    parser.run()
    print("Successful")
    input("Press any key for exit!")
    

