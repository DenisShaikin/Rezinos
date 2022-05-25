
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import selenium as se
import numpy as np
import pandas as pd
import time
from sqlalchemy import func
from app import db, celery
from app.api.apimodels import ApiTire
from datetime import datetime, timedelta
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
    df=df.loc[~(df['qte'].isnull() & df['price'].isnull())]
    currMode=pd.options.mode.chained_assignment
    pd.options.mode.chained_assignment=None
    df=df.loc[df['qte']>0] #Чтобы не получить бесконечность
    df['unitPrice']=df['price']/df['qte']
    df['unitPrice']=df['unitPrice'].round(2)
    # df=df.loc[(~np.isfinite(df['unitPrice']))]  #убираем бесконечность - где qte=0
    # df.loc[df['unitPrice']<1000, 'unitPrice']=df.loc[df['unitPrice']<1000, 'price']
    df['wear_num'] = pd.to_numeric(df['wear'].str.rstrip('%'), errors='coerce') / 100
    pd.options.mode.chained_assignment=currMode
    #Убираем без износа и с 0 износом
    # df.to_csv(r'c:\Users\au00449\Python Marketing\Data\df1.csv', sep=';', encoding='utf-8')
    # print(df.loc[~df.wear.isnull()].head())
    #убираем износ =0
    # df=df.loc[df['wear_num']>=0]
    df.drop('0', axis='columns', inplace=True)
    return df

#расчет расстояния между точками - поскольку малые расстояния то считаем на плоскости попрямой
def calculateTheDistance (shir_A, dolg_A, shir_B, dolg_B):
    if shir_B and shir_A and dolg_B and dolg_A:
        distance= ((shir_B - shir_A) * (shir_B - shir_A) + (dolg_B - dolg_A) * (dolg_B - dolg_A)) ** (0.5)
        return distance
    else :
        return None

def getAvitoCoordinates(app):
    app.app_context().push()
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
    caps = se.webdriver.DesiredCapabilities.CHROME.copy()
    caps['acceptInsecureCerts'] = True
    caps['acceptSslCerts'] = True
    driver = se.webdriver.Chrome(desired_capabilities=caps, options=options)
    driver.get('https://www.avito.ru/')
    time.sleep(2)
    with app.app_context():
        avitoTires = db.session.query(ApiTire.id, ApiTire.avito_link, ApiTire.avito_lon, ApiTire.avito_lat).filter(ApiTire.avito_lon == None).all()
        # print(avitoTires)
        for tire in avitoTires:
            print(tire.avito_link)
            strLink=tire.avito_link
            driver.get(strLink)
            WebDriverWait(driver, 15) \
                .until(EC.any_of(
                EC.visibility_of_any_elements_located((By.XPATH, "//div[contains(@class,'gallery-img-frame js-gallery-img-frame')]")),
                EC.visibility_of_any_elements_located((By.XPATH, "//h3[contains(@class,'title-listRedesign-_rejR')]")),
                EC.visibility_of_any_elements_located((By.XPATH, "//span[contains(@class,'item-closed-warning__content')]"))
            ))
            # WebDriverWait(driver, 10).until(EC.visibility_of_any_elements_located((By.XPATH, ['gallery-img-frame js-gallery-img-frame'])))
            # time.sleep(2)
            if driver.current_url==strLink:  #Значит не было редиректа, работаем
                lon=None
                lat=None
                itemImg = None
                try:
                    itemImg = WebDriverWait(driver, 3).until(
                        EC.presence_of_element_located((By.XPATH, "//div[contains(@class,'gallery-img-frame js-gallery-img-frame')]")))  #Здесь картинка
                except:
                    item=EC.presence_of_element_located(
                        (By.XPATH, "//span[contains(@class,'item-closed-warning__content')]"))  # Здесь надпись объявление снято
                    # print(item.text)
                    itemImg = None
            #         pass

                if itemImg:
                    db.session.query(ApiTire).filter(ApiTire.id == tire.id). \
                        update({ApiTire.avito_imgLink: itemImg.get_attribute('data-url')}, synchronize_session="evaluate") #ссылка на картинку
                    try:
                        itemPage = driver.find_element(by=By.XPATH, value="//div[contains(@class,'b-search-map item-map-wrapper')]")
                        lat = itemPage.get_attribute('data-map-lat')  # Сохраним все заголовки
                        lon = itemPage.get_attribute('data-map-lon')  # Сохраним все заголовки
                    except:
                        pass
                if lon:
                    db.session.query(ApiTire).filter(ApiTire.id == tire.id). \
                        update({ApiTire.avito_lon: float(lon)}, synchronize_session="evaluate")
                if lat:
                    db.session.query(ApiTire).filter(ApiTire.id == tire.id). \
                        update({ApiTire.avito_lat: float(lat)}, synchronize_session="evaluate")
                print(lon, lat)

                db.session.commit()
                time.sleep(2)
    driver.close()
    return 'Success'

@celery.task(bind=True)
def getAvitoTirePrices(self, diametr, width, height, region='rossiya', season='zimnie_neshipovannye', nPages=10):
    # app.app_context().push()
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
    # print('diametr={}, season={}, width={}, height={}'.format(diametr, season, width, height))
    pd.set_option('display.max_colwidth', 1000)
    print(strLink)
#     options.add_argument('headless')
#     driver = se.webdriver.Chrome(options=options)
    caps = se.webdriver.DesiredCapabilities.CHROME.copy()
    caps['acceptInsecureCerts'] = True
    caps['acceptSslCerts'] = True
    driver = se.webdriver.Chrome(desired_capabilities=caps, options=options)

    dfResult=pd.DataFrame()
    print(strLink)
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
                brandsList=[brand.text for brand in brands] #Сохраним все заголовки
                codes = driver.find_elements(by=By.XPATH, value="//a[contains(@class,'title-listRedesign-_rejR')]")
                # print(codes)
                codesList = [code.get_attribute("href").split('_')[-1] for code in codes] #ID объявлений

                #Собираем цены без спец предложений!
                avitoLinks = driver.find_elements(by=By.XPATH, value="//a[contains(@class,'title-listRedesign-_rejR')]")
                avitoLinksList = [link.get_attribute("href") for link in avitoLinks]  # Сохраним все ссылки на объявления в список
                #Собираем цены
                prices=driver.find_elements(by=By.XPATH, value="//span[@class='price-root-RA1pj price-listRedesign-GXB2V']")
                pricesList=[]
                for element in prices:
                    realPrice=element.find_element(by=By.XPATH, value=".//span[contains(@class,'price-text-_YGDY')]")
                    pricesList.append(realPrice.text)
                #Сезонность
                seasons=driver.find_elements(by=By.XPATH, value="//span[contains(@class,'iva-item-text-Ge6dR text-text-LurtD')]")
                seasonList=[season.text for season in seasons]

                #Все соединяем только если длины списков совпадают!
                if len(metaList) == len(brandsList) and len(metaList)==len(pricesList) and \
                        len(metaList)==len(seasonList) and len(metaList)==len(avitoLinksList):
                    dfTempResult=pd.DataFrame(data = metaList)
                    dfTempResult=dfTempResult.assign(brand = brandsList)
                    dfTempResult=dfTempResult.assign(price = pricesList)
                    dfTempResult=dfTempResult.assign(season = seasonList)
                    dfTempResult=dfTempResult.assign(avito_id = codesList)
                    dfTempResult=dfTempResult.assign(avito_link =avitoLinksList)
                    dfTempResult['regionReal'] = dfTempResult['avito_link'].apply(lambda x: x.split('/')[3]) #Регион из ссылки - реальный регион

#                     dfTempResult=dfTempResult.assign(geo = geoList)
                    dfTempResult['region']= region
                    #В параметрах может не приходить размер, тогда его можно взять из заголовка
                    dfTempResult['size'] = dfTempResult['brand'].str.extract('(\d{3}\/\d{2,3}\sR\d{1,2})', expand=False)
                    dfTempResult['sizeDiametr'] = dfTempResult['size'].str.extract('(R\d{1,2})', expand=False) #Выбираем только диаметр, бывает NaN
                    dfTempResult['size'] = dfTempResult['brand'].str.extract('(\d{3}\/\d{2,3})', expand=False) #Оставляем только ширину и высоту профиля
                    if diametr:
                        dfTempResult['diametr']=diametr
                    else:
                        dfTempResult['diametr']=dfTempResult['size'].str.extract('(R\d{1,2})', expand=False)
                    if width:
                        dfTempResult['width']=width
                    else:
                        dfTempResult['width'] = pd.to_numeric(dfTempResult['size'].str.extract('(\d{3})', expand=False), errors='coerce').astype('Int32', errors='ignore')
                    if height:
                        dfTempResult['height'] = height
                    else:
                        dfTempResult['height'] = dfTempResult['size'].str.extract('(\/\d{2,3})', expand=False) #Высота бывает 2 или 3 знака
                        dfTempResult['height'] = pd.to_numeric(dfTempResult['height'].str.replace('/', ''), errors='coerce').astype('int32', errors='ignore')
                    dfTempResult.drop(columns=['size','sizeDiametr'], axis=1, inplace=True)
                    dfTempResult['wear'] = dfTempResult[0].str.extract('(\Sзнос\s.{,3})', expand=False)
                    dfTempResult['wear2'] = dfTempResult[0].str.extract('(\d{2}%)', expand=False)
                    #Вычищаем данные
                    dfTempResult=treatAvitoTiresData(dfTempResult)
                    dfTempResult['request_type'] = 0 #значит добавляем скан без геолокации и радиуса поиска
                    dfResult=pd.concat([dfResult, dfTempResult])

                    #Добавляем новые записи в базу
                    # with app.app_context():
                    # Проверяем эти записи в базе и уже существующие удаляем из базы
                    # print(codesList)
                    # query = db.session.query(ApiTire).filter(ApiTire.avito_id.in_(codesList))
                    # print(query.statement)
                    db.session.query(ApiTire).filter(ApiTire.avito_id.in_(codesList)).delete(synchronize_session='fetch')
                    db.session.commit()
                    #Так же надо удалить записи старше месяца
                    oldDate = datetime.today() - timedelta(days=15)
                    db.session.query(ApiTire).filter(ApiTire.update_date < oldDate).delete(synchronize_session='fetch')
                    db.session.commit()

                    # необходимо ручками присвоить id с max до длины нового набора, иначе они будут пустыми
                    lastRec = db.session.query(func.max(ApiTire.id)).one()[0]
                    lastRec = 0 if not lastRec else lastRec
                    dfTempResult['index'] = range(lastRec + 1, lastRec + len(dfTempResult) + 1)
                    dfTempResult.set_index('index', inplace=True)
                    dfTempResult.index.name = 'id'
                    dfTempResult['update_date'] = datetime.utcnow()
                    dfTempResult.to_sql('tire_api', con=db.engine, if_exists='append', index=False)  # dtype={'id': db.Integer}
            else:
                time.sleep(3)
    driver.quit()
    # currTire=Tire()
    # myapp=app._get_current_object()
    return dfResult

@celery.task(bind=True)
def getAvitoTirePricesByLocale(self, diametr, width, height, lon, lat, region, season='zimnie_neshipovannye', nPages=10, distance=50):
    # app.app_context().push()
    options = se.webdriver.ChromeOptions()
    options.add_argument('User-Agent=Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; rv:11.0) like Gecko')
    options.add_argument('Connection=keep-alive')
    options.add_argument('Accept=text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8')
    options.add_argument('Accept-Language=ru-ru,ru;q=0.8,en-us;q=0.6,en;q=0.4')
    # options.add_argument('headless')
    options.add_argument('disable-dev-shm-usage')
    options.add_argument('no-sandbox')  #--no-sandbox
    options.add_argument('--disable-gpu')
    options.add_argument('allow-running-insecure-content')
    options.add_argument('--ignore-certificate-errors-spki-list')
    options.add_argument("--ignore-certificate-error")
    options.add_argument("--ignore-ssl-errors")
    options.add_argument('log-level=3')
    # print('регион=',region)
    strLink='https://www.avito.ru/' + str(region) + '/zapchasti_i_aksessuary/shiny_diski_i_kolesa/shiny/'
    if diametr:
        strLink +='diametr_' + str(diametr)
    if season:
        strLink +='/' + str(season)
    if width:
        strLink +='/' + 'shirina_' + str(width)
    if height:
        strLink +='/' + 'vysota_' + str(height)
    # print('diametr={}, season={}, width={}, height={}'.format(diametr, season, width, height))
    pd.set_option('display.max_colwidth', 1000)
    # print(strLink)
#     options.add_argument('headless')
#     driver = se.webdriver.Chrome(options=options)
    caps = se.webdriver.DesiredCapabilities.CHROME.copy()
    caps['acceptInsecureCerts'] = True
    caps['acceptSslCerts'] = True
    driver = se.webdriver.Chrome(desired_capabilities=caps, options=options)

    #Удалим все существующие записи
    # with app.app_context():
    db.session.query(ApiTire).filter(ApiTire.request_type == 1).delete(synchronize_session='fetch')
    db.session.commit()

    dfResult=pd.DataFrame()
    strLink += '?geoCoords=' + str(lat) +  '%2C' + str(lon) + '&radius=' + str(distance)
    print(strLink)

    try:
        driver.get(strLink)
    except:
        time.sleep(10)
        driver.get(strLink)
    time.sleep(1)

    #Определим количество страниц
    pagesNumber=driver.find_elements(by=By.XPATH, value="//span[contains(@class,'pagination-item-JJq_j')]")
    if len(pagesNumber)==0:
        time.sleep(10)
        driver.get(strLink)
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
            print(strLink  + '&p=' + str(p))
            try:
                driver.get(strLink  + '&p=' + str(p)) #+ '-'+ token
            except:
                time.sleep(10)
                driver.get(strLink + '&p=' + str(p))
            time.sleep(1)
            metaDescription=driver.find_elements(by=By.XPATH, value="//div[contains(@class,'iva-item-text-Ge6dR iva-item-description-FDgK4 text-text-LurtD text-size-s-BxGpL')]")
            metaList=[meta.text for meta in metaDescription] #Сохраним все ссылки в список    # print(metaList)
            if len(metaList)>0:
                brands=driver.find_elements(by=By.XPATH, value="//h3[contains(@class,'title-listRedesign-_rejR')]")
                brandsList=[brand.text for brand in brands] #Сохраним все заголовки
                codes = driver.find_elements(by=By.XPATH, value="//a[contains(@class,'title-listRedesign-_rejR')]")
                # print(codes)
                codesList = [code.get_attribute("href").split('_')[-1] for code in codes] #ID объявлений

                #Собираем цены без спец предложений!
                avitoLinks = driver.find_elements(by=By.XPATH, value="//a[contains(@class,'title-listRedesign-_rejR')]")
                avitoLinksList = [link.get_attribute("href") for link in avitoLinks]  # Сохраним все ссылки на объявления в список
                #Собираем цены
                prices=driver.find_elements(by=By.XPATH, value="//span[@class='price-root-RA1pj price-listRedesign-GXB2V']")
                pricesList=[]
                for element in prices:
                    realPrice=element.find_element(by=By.XPATH, value=".//span[contains(@class,'price-text-_YGDY')]")
                    pricesList.append(realPrice.text)
                #Сезонность
                seasons=driver.find_elements(by=By.XPATH, value="//span[contains(@class,'iva-item-text-Ge6dR text-text-LurtD')]")
                seasonList=[season.text for season in seasons]

                #Все соединяем только если длины списков совпадают!
                if len(metaList) == len(brandsList) and len(metaList)==len(pricesList) and \
                        len(metaList)==len(seasonList) and len(metaList)==len(avitoLinksList):
                    dfTempResult=pd.DataFrame(data = metaList)
                    dfTempResult=dfTempResult.assign(brand = brandsList)
                    dfTempResult=dfTempResult.assign(price = pricesList)
                    dfTempResult=dfTempResult.assign(season = seasonList)
                    dfTempResult=dfTempResult.assign(avito_id = codesList)
                    dfTempResult=dfTempResult.assign(avito_link =avitoLinksList)
                    dfTempResult['regionReal'] = dfTempResult['avito_link'].apply(lambda x: x.split('/')[3]) #Регион из ссылки - реальный регион

#                     dfTempResult=dfTempResult.assign(geo = geoList)
                    dfTempResult['region']= region
                    #В параметрах может не приходить размер, тогда его можно взять из заголовка
                    dfTempResult['size'] = dfTempResult['brand'].str.extract('(\d{3}\/\d{2,3}\sR\d{1,2})', expand=False)
                    dfTempResult['sizeDiametr'] = dfTempResult['size'].str.extract('(R\d{1,2})', expand=False) #Выбираем только диаметр, бывает NaN
                    dfTempResult['size'] = dfTempResult['brand'].str.extract('(\d{3}\/\d{2,3})', expand=False) #Оставляем только ширину и высоту профиля
                    if diametr:
                        dfTempResult['diametr']=diametr
                    else:
                        dfTempResult['diametr']=dfTempResult['size'].str.extract('(R\d{1,2})', expand=False)
                    if width:
                        dfTempResult['width']=width
                    else:
                        dfTempResult['width'] = pd.to_numeric(dfTempResult['size'].str.extract('(\d{3})', expand=False), errors='coerce').astype('Int32', errors='ignore')
                    if height:
                        dfTempResult['height'] = height
                    else:
                        dfTempResult['height'] = dfTempResult['size'].str.extract('(\/\d{2,3})', expand=False) #Высота бывает 2 или 3 знака
                        dfTempResult['height'] = pd.to_numeric(dfTempResult['height'].str.replace('/', ''), errors='coerce').astype('int32', errors='ignore')
                    dfTempResult.drop(columns=['size','sizeDiametr'], axis=1, inplace=True)
                    dfTempResult['wear'] = dfTempResult[0].str.extract('(\Sзнос\s.{,3})', expand=False)
                    dfTempResult['wear2'] = dfTempResult[0].str.extract('(\d{2}%)', expand=False)
                    #Вычищаем данные
                    dfTempResult=treatAvitoTiresData(dfTempResult)
                    dfTempResult['request_type'] = 1 #значит добавляем скан по геолокации  и радиусу
                    dfResult=pd.concat([dfResult, dfTempResult])

                    #Добавляем новые записи в базу
                    # with app.app_context():
                    # необходимо ручками присвоить id с max до длины нового набора, иначе они будут пустыми
                    lastRec = db.session.query(func.max(ApiTire.id)).one()[0]
                    lastRec = 0 if not lastRec else lastRec
                    dfTempResult['index'] = range(lastRec + 1, lastRec + len(dfTempResult) + 1)
                    dfTempResult.set_index('index', inplace=True)
                    dfTempResult.index.name = 'id'
                    dfTempResult['update_date'] = datetime.utcnow()
                    dfTempResult.to_sql('tire_api', con=db.engine, if_exists='append', index=False)  # dtype={'id': db.Integer}
            else:
                time.sleep(3)
    driver.quit()
    # currTire=Tire()
    # myapp=app._get_current_object()
    return len(dfResult)  #Возвращаем количество добавленных записей

# def updateTires(app, region, season, diametr, width, height, pages=20):
#     dfUpdateBase=getAvitoTirePrices(app, diametr, width, height, region, season, pages)
#     # print(dfUpdateBase.head())
#     return dfUpdateBase

def getAvitoAccountData(id):
    options = se.webdriver.ChromeOptions()
    # options.add_argument('--proxy-server=138.21.89.91:3128');
    # options.add_argument('--Proxy-Authorization=au00449:88akakiy')
    options.add_argument('User-Agent=Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; rv:11.0) like Gecko')
    options.add_argument('Connection=keep-alive')
    options.add_argument('Accept=text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8')
    options.add_argument('Accept-Language=ru-ru,ru;q=0.8,en-us;q=0.6,en;q=0.4')
    options.add_argument("start-maximized")

    driver = se.webdriver.Chrome(options=options,
                                 executable_path='c:/Users/au00449/Python Marketing/chromedriver/chromedriver.exe')
    dfResult = pd.DataFrame()

    try:
        driver.get('https://www.avito.ru/i182209893')
    #             break
    except:
        time.sleep(10)
        driver.get('https://www.avito.ru/i182209893')
    time.sleep(1)

    time.sleep(1)
    avitolinks = driver.find_elements(by=By.XPATH, value="//a[contains(@class, 'item-description-title-link')]")
    avitolinksList = [link.get_attribute("href") for link in avitolinks]
    # print(avitolinksList)
    for link in avitolinksList:
        driver.get(link)
        time.sleep(5)
        title = driver.find_element(by=By.XPATH, value="//span[contains(@class, 'title-info-title-text')]").text
        #     titlesList = [title.text for title in titles]
        photos = driver.find_elements(by=By.XPATH, value="//div[contains(@class, 'gallery-img-frame')]")
        photosList = [photo.get_attribute("data-url") for photo in photos]
        #     photo = driver.find_element(by=By.XPATH, value="//div[contains(@class, 'gallery-img-frame')]").get_attribute('data-url')
        price = driver.find_element(by=By.XPATH, value="//span[contains(@class, 'js-item-price')]").get_attribute("content")
        characts = driver.find_elements(by=By.XPATH, value="//li[contains(@class, 'item-params-list-item')]")  # item-params-list-item
        charactsList = [char.text for char in characts]
        description = driver.find_element(by=By.XPATH, value="//div[contains(@class, 'item-description-html')]").text
        #     charactsList.append(title, photo, price, description)
        #     mydf=pd.DataFrame(data=charactsList)
        dataDict = dict()
        dataDict['title'] = title
        dataDict['price'] = price
        dataDict['description'] = description

        if charactsList:  # Переводим list в dict
            for item in charactsList:
                dataDict[item.split(':')[0]] = item.split(':')[1]

        break

    driver.close()
