
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
import selenium as se
import numpy as np
import pandas as pd
import time
from sqlalchemy import func
from app import db
from app.api.apimodels import ApiTire
from datetime import datetime
from flask_restful import abort

def treatAvitoTiresData(df):
    df.rename(columns={0:'0'}, inplace=True)
    df['qte2'] = df['brand'].str.extract('(\d{1}\sшт)', expand=False)
    df['qte2']=df['qte2'].apply(lambda x: str(x).replace('шт',''))
    df['qte3']=df['0'].str.extract('((?i)цена\s\w*\s\w*\s\w*|стоимость\s\w*\s\w*\s\w*\s\w*|цена\s\w*\s\w*\s\w*\s\w*|цена\sза\sшт\w*|за\sодин|цена\sза\s\w*)', expand=False)
    df['qte2']=df['qte2'].str.strip()
    df['qte2']=pd.to_numeric(df['qte2'], errors='coerce')
    #Убираем цены
    df['qte3'] = df['qte3'].str.replace(r'\d{4}|\dК|\dк', '', regex=True)
    #обрабатываем варианты цена за 1 колесо
    df['qte4'] = df['qte3'].str.replace(r'(?i)кажд\w*|за\sод\w*|за\sшт|за\sколесо|за\sшин\w*|за\sшту\w*', '1', regex=True)
    #обрабатываем варианты цена за 4 колеса
    df['qte4'] = df['qte4'].str.replace(r'(?i)за\sкомплект\s4|за\sкомплект', '4', regex=True)
    #обрабатываем варианты цена за пару
    df['qte4'] = df['qte4'].str.replace(r'(?i)за\sпар\w*|за\sдв\w', '2', regex=True)
    df['qteFinal']=df['qte4'].str.extract('(\d)', expand=False)
    df['qteFinal']=pd.to_numeric(df['qteFinal'], errors='coerce')
    cond1 = (df['qte2'].isnull()) & (~df['qteFinal'].isnull())  #Тогда присвоим qteFinal
    cond2 = df['qteFinal'] <= df['qte2']  #Тогда присвоим qteFinal, то есть меньшее
    cond3 = (~df['qte2'].isnull()) & (df['qteFinal'].isnull()) #Тогда присваиваем qte2
    df['qte'] = np.select([cond1, cond2, cond3], [df['qteFinal'], df['qteFinal'], df['qte2']], np.NaN)
    #Займемся износом
    df['0']=df['0'].str.replace(': ',' ')
    df['0']=df['0'].str.replace('~',' ')
    df['wear2'] = df['0'].str.extract('((?i)изно\w*(\s\w*){0,5}\d{1,2}%|изно\w*(\s\w*){0,5}\d{1,2}-\d{1,2}%|новы\w*|(?i)изно\w*(\s\—\s\w*\s){0,5}\d{1,2}\%|\d{1,2}\%\sизно\w*)', expand=False)[0]
    df['wear2'] = df['wear2'].str.replace('((?i)новы\w*)', '00%', regex=True)
    df['wear3'] = df['wear2'].str.extract('(\d{1,2}-\d{1,2}%)', expand=False)
    df['wear3']=df['wear3'].str.split('-')
    df['wear3']=df['wear3'].apply(lambda x: x[1] if x is not np.NaN else np.NaN)
    df['wear2'] = df['wear2'].str.extract('(\d{1,2}%)', expand=False) #Оставляем только цифру износа
    cond1 = (~df['wear3'].isnull())  #Тогда присвоим wear3
    cond2 = (~df['wear2'].isnull())  #Тогда присваиваем wear2
    df['wear'] = np.select([cond1, cond2], [df['wear3'], df['wear2']], np.NaN)
    df.drop(columns=['qte2', 'qte3', 'qte4', 'wear2', 'wear3', 'qteFinal'], inplace=True)
    df['price']=df['price'].str.replace('₽', '').str.replace(' ', '')
    df['price']=df['price'].str.replace(' ', '')
#     print(dtypes(df['price']))
    df['price']=df['price'].apply(pd.to_numeric, errors='coerce')  #pd.to_numeric(df['price'], errors='coerce')
    df=df.loc[~df['qte'].isnull()]
    currMode=pd.options.mode.chained_assignment
    pd.options.mode.chained_assignment=None
    df['unitPrice']=df['price']/df['qte']
    # df.loc[df['unitPrice']<1000, 'unitPrice']=df.loc[df['unitPrice']<1000, 'price']
    df['wear_num'] = pd.to_numeric(df['wear'].str.rstrip('%'), errors='coerce') / 100
    pd.options.mode.chained_assignment=currMode
    #Убираем без износа и с 0 износом
    df.to_csv(r'c:\Users\au00449\Python Marketing\Data\df1.csv', sep=';', encoding='utf-8')
    # print(df.loc[~df.wear.isnull()].head())
    df=df.loc[df['wear_num']>=0]

    df.drop('0', axis='columns', inplace=True)
    return df

def getAvitoTirePrices(app, diametr, width, height, region='rossiya', season='zimnie_neshipovannye', nPages=10):
    options = se.webdriver.ChromeOptions()
    options.add_argument('User-Agent=Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; rv:11.0) like Gecko')
    options.add_argument('Connection=keep-alive')
    options.add_argument('Accept=text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8')
    options.add_argument('Accept-Language=ru-ru,ru;q=0.8,en-us;q=0.6,en;q=0.4')
    options.add_argument('headless')
    options.add_argument('disable-dev-shm-usage')
    options.add_argument('no-sandbox')  #--no-sandbox
    options.add_argument('--disable-gpu')
    options.add_argument('allow-running-insecure-content')
    options.add_argument('--ignore-certificate-errors-spki-list')
    options.add_argument("--ignore-certificate-error")
    options.add_argument("--ignore-ssl-errors")
    options.add_argument('log-level=3')
    # print('регион=',region)
    strLink='https://www.avito.ru/' + region + '/zapchasti_i_aksessuary/shiny_diski_i_kolesa/shiny/'
    if diametr:
        strLink +='diametr_' + str(diametr)
    if season:
        strLink +='/' + str(season)
    if width:
        strLink +='/' + 'shirina_' + str(width)
    if height:
        strLink +='/' + 'vysota_' + str(height)
    print(strLink)
#     options.add_argument('headless')
#     driver = se.webdriver.Chrome(options=options)
    caps = se.webdriver.DesiredCapabilities.CHROME.copy()
    caps['acceptInsecureCerts'] = True
    caps['acceptSslCerts'] = True
    driver = se.webdriver.Chrome(desired_capabilities=caps, options=options)

    dfResult=pd.DataFrame()
    try:
        driver.get(strLink + '?localPriority=1')
    except:
        time.sleep(10)
        driver.get(strLink + '?localPriority=1')
    time.sleep(1)

    #Определим количество страниц
    pagesNumber=driver.find_elements(by=By.XPATH, value="//span[contains(@class,'pagination-item-JJq_j')]")
    if len(pagesNumber)==0:
        time.sleep(10)
        driver.get(strLink + '?localPriority=1')
        time.sleep(1)
        pagesNumber=driver.find_elements(by=By.XPATH, value="//span[contains(@class,'pagination-item-JJq_j')]")
#             print(pagesNumber)
    else:
        pagesList=[page.text for page in pagesNumber]
        dfPages=pd.DataFrame(data=pagesList, columns=['page'])
        dfPages['page']=pd.to_numeric(dfPages['page'], errors='coerce')
        pagesNum=int(dfPages['page'].max())
        pagesNum = nPages if pagesNum>nPages else pagesNum #По nPages страниц с каждого региона
        for p in range(1, pagesNum+1):
            print('Страница:', p)
            print(strLink  + '?p=' + str(p) + '&localPriority=1')
            try:
                driver.get(strLink  + '?p=' + str(p) + '&localPriority=1') #+ '-'+ token
            except:
                time.sleep(10)
                driver.get(strLink + '?p=' + str(p) +'&localPriority=1')
            time.sleep(1)
            metaDescription=driver.find_elements(by=By.XPATH, value="//div[contains(@class,'iva-item-text-Ge6dR iva-item-description-FDgK4 text-text-LurtD text-size-s-BxGpL')]")
            metaList=[meta.text for meta in metaDescription] #Сохраним все ссылки в список    # print(metaList)
            if len(metaList)>0:
                brands=driver.find_elements(by=By.XPATH, value="//h3[contains(@class,'title-listRedesign-_rejR')]")
                brandsList=[brand.text for brand in brands] #Сохраним все ссылки в список
                #Собираем цены без спец предложений!
                prices=driver.find_elements(by=By.XPATH, value="//span[@class='price-root-RA1pj price-listRedesign-GXB2V']")
                pricesList=[]
                for element in prices:
                    realPrice=element.find_element(by=By.XPATH, value=".//span[contains(@class,'price-text-_YGDY')]")
                    pricesList.append(realPrice.text)
                seasons=driver.find_elements(by=By.XPATH, value="//span[contains(@class,'iva-item-text-Ge6dR text-text-LurtD')]")
                seasonList=[season.text for season in seasons]

                #Все соединяем только если длины списков совпадают!
                if len(metaList) == len(brandsList) and len(metaList)==len(pricesList) and len(metaList)==len(seasonList):
                    dfTempResult=pd.DataFrame(data = metaList)
                    dfTempResult=dfTempResult.assign(brand = brandsList)
                    dfTempResult=dfTempResult.assign(price = pricesList)
                    dfTempResult=dfTempResult.assign(season = seasonList)
#                     dfTempResult=dfTempResult.assign(geo = geoList)
                    dfTempResult['region']= region
                    dfTempResult['diametr']=diametr
                    dfTempResult['width']=width
                    dfTempResult['height']=height
                    dfTempResult['wear'] = dfTempResult[0].str.extract('(\Sзнос\s.{,3})', expand=False)
                    dfTempResult['wear2'] = dfTempResult[0].str.extract('(\d{2}%)', expand=False)
                    #Вычищаем данные
                    dfTempResult=treatAvitoTiresData(dfTempResult)
                    dfResult=pd.concat([dfResult, dfTempResult])
            else:
                time.sleep(3)
    driver.quit()
    # currTire=Tire()
    # myapp=app._get_current_object()
    app.app_context().push()
    with app.app_context():
        #необходимо ручками присвоить id с max до длины нового набора, иначе они будут пустыми
        lastRec=db.session.query(func.max(ApiTire.id)).one()[0]
        lastRec=0 if not lastRec else lastRec

        dfResult['index']=range(lastRec+1, lastRec+len(dfResult)+1)
        dfResult.set_index('index', inplace=True)
        dfResult.index.name = 'id'
        dfResult['update_date']=datetime.utcnow()
        dfResult.to_sql('tire_api', con=db.engine, if_exists='append', index=True) #dtype={'id': db.Integer}
    return dfResult

def updateTires(app, region, season, diametr, width, height, pages=20):
    dfUpdateBase=getAvitoTirePrices(app, diametr, width, height, region, season, pages)
    # print(dfUpdateBase.head())
    return dfUpdateBase
