#!/usr/bin/python
# coding=utf-8

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
import csv
import codecs
import sys
import urllib
import httplib
import requests
import json

def unicode_csv_reader(utf8_data, dialect=csv.excel, **kwargs):
        csv_reader = csv.reader(utf8_data, dialect=dialect, **kwargs)
        for row in csv_reader:
            yield [unicode(cell, 'utf-8') for cell in row]

def remove_first_line_from_file(authors_file_name):
    with codecs.open(authors_file_name, 'r', encoding='utf-8') as fin:
        data = fin.read().splitlines(True)
    with codecs.open(authors_file_name, 'w', encoding='utf-8') as fout:
        fout.writelines(data[1:])

def assure_path_exists(path):
        dir = os.path.dirname(path)
        if not os.path.exists(dir):
                os.makedirs(dir)

def convertCaptchatoBase64(drive):
    imgBase64 = drive.execute_script("""
    var img = window.document.getElementById('image_captcha');
    // Create an empty canvas element
    var canvas = window.document.createElement("canvas");
    canvas.width = img.width;
    canvas.height = img.height;

    // Copy the image contents to the canvas
    var ctx = canvas.getContext("2d");
    ctx.drawImage(img, 0, 0);



    var dataURL = canvas.toDataURL("image/png");

    return dataURL.replace(/^data:image\/(png|jpg);base64,/, "");
    """)
    return imgBase64



if __name__ == '__main__':
    
    if (len(sys.argv)>1):
        prefix_file_name = sys.argv[1]
        authors_file_name = prefix_file_name+'_authors.csv'
        downloaded_file_name = prefix_file_name+'_downloaded.csv'
        error_file_name = prefix_file_name+'_error.csv'
        not_found_file_name = prefix_file_name+'_not_found.csv'
    else:
        authors_file_name = 'authors.csv'
        downloaded_file_name = 'downloaded.csv'
        error_file_name = 'error.csv'
        not_found_file_name = 'not_found.csv'

    try:
        assure_path_exists(os.getcwd()+'/data')
    except:
        sys.exit('Erro ao criar o diretório '+os.getcwd()+'/data')

    ids_downloaded = os.listdir(os.getcwd()+'/data')

    profile = webdriver.FirefoxProfile()
    profile.set_preference('permissions.default.stylesheet', 2)
    profile.set_preference('dom.ipc.plugins.enabled.libflashplayer.so', 'false')
    profile.set_preference('browser.download.dir', os.getcwd()+'/data')
    profile.set_preference('browser.download.folderList', 2)
    profile.set_preference('browser.helperApps.neverAsk.saveToDisk', 'application/zip')
    driver = webdriver.Firefox(firefox_profile=profile)
    driver.implicitly_wait(3)
    base_url = 'http://buscatextual.cnpq.br/buscatextual'
    
    while os.stat(authors_file_name).st_size != 0:
        try:
            csv_reader = unicode_csv_reader(open(authors_file_name))
        except:
            sys.exit('Erro ao abrir o arquivo '+authors_file_name)
        
        row = next(csv_reader)
        author_uri = row[0]
        author_name = row[1]
        paper_title = row[2].encode('utf-8')
        paper_title2 = row[3].encode('utf-8')

        driver.get(base_url)
        driver.find_element_by_id('textoBusca').clear()
        driver.find_element_by_id('textoBusca').send_keys(author_name)
        driver.find_element_by_id('buscarDemais').click()
        driver.find_element_by_id('botaoBuscaFiltros').click()

        if not 'Nenhum resultado foi encontrado para:' in driver.page_source.encode('utf-8'):
            resultado_geral = driver.find_element_by_class_name('resultado')
            resultados = resultado_geral.find_elements_by_tag_name('a')
            ids = []

            for resultado in resultados:
                ids.append(resultado.get_attribute('href')[24:34])
            
            paper_found = False
            for id in ids:
                if not paper_found:
                    print(author_name.encode('utf-8')+' - '+paper_title)
                    print(base_url+'/visualizacv.do?id='+id)
                    driver.get(base_url+'/visualizacv.do?id='+id)

                    # QUEBRAR CAPTCHA #

                    button = driver.find_element_by_id('btn_validar_captcha')
                    while True:

                        print button.is_displayed()
                        imgBase64 = convertCaptchatoBase64(driver)

                        r = requests.post('http://192.168.200.84:8080/CaptchaService/captcha', data = json.dumps({'imgBase64':imgBase64}))

                        r.encoding = "UTF-8"
                        jsonCaptcha = r.json()

                        driver.find_element_by_id('informado').clear()
                        driver.find_element_by_id('informado').send_keys(jsonCaptcha['captcha'])
                        driver.find_element_by_id('btn_validar_captcha').click()
                        try:
                            page_source = driver.page_source.encode('utf-8')
                            informacoes_autor = driver.find_element_by_class_name('informacoes-autor')
                            break
                        except:
                            print "Tentar Novamente"
                    print "Quebrou"

                    if (paper_title.lower().replace(' ', '') in page_source.lower().replace(' ', '') or paper_title2.lower().replace(' ', '') in page_source.lower().replace(' ', '')):
                        paper_found = True
                        id_autor_xml = informacoes_autor.find_element_by_tag_name('li')
                        id_autor_xml = id_autor_xml.text[-16:]

                        if not (id_autor_xml+'.zip') in ids_downloaded:
                            print(base_url+'/download.do?idcnpq='+id_autor_xml)
                            driver.get(base_url+'/download.do?idcnpq='+id_autor_xml)
                            while driver.findElement(By.ID("btn_validar_captcha")):

                                imgBase64 = convertCaptchatoBase64(driver)

                                r = requests.post('http://192.168.200.84:8080/CaptchaService/captcha', data = json.dumps({'imgBase64':imgBase64}))

                                r.encoding = "UTF-8"
                                jsonCaptcha = r.json()

                                driver.find_element_by_id('informado').clear()
                                driver.find_element_by_id('informado').send_keys(jsonCaptcha['captcha'])
                                driver.find_element_by_id('btn_validar_captcha').click()

                                ids_downloaded.append(id_autor_xml+'.zip')
                                WebDriverWait(driver, 1)
                        with open(downloaded_file_name, 'a') as downloaded_file:
                            try:
                                downloaded_file.write('"'+author_uri.encode('utf-8')+'","http://www.ic.ufal.br/dac/author/lattes/'+id_autor_xml+'","'+author_name.encode('utf-8')+'","'+paper_title+'","'+paper_title2+'"\n')
                            except:
                                driver.quit()
                                sys.exit('Erro ao escrever no arquivo '+downloaded_file_name)
                        break

            if not paper_found:
                with open(error_file_name, 'a') as error_file:
                    try:
                        error_file.write('"'+author_name.encode('utf-8')+'","'+paper_title+'"\n')
                    except:
                        driver.quit()
                        sys.exit('Erro ao escrever no arquivo '+error_file_name)

        else:
            with open(not_found_file_name, 'a') as not_found_file:
                try:
                    not_found_file.write('"'+author_name.encode('utf-8')+'","'+paper_title+'"\n')
                except:
                    driver.quit()
                    sys.exit('Erro ao escrever no arquivo '+not_found_file_name)

        try:
            remove_first_line_from_file(authors_file_name)
        except:
            driver.quit()
            sys.exit('Erro ao tentar remover a primeira linha do arquivo '+authors_file_name)

    driver.quit()
    print ('\n\nOK!\n')
