/*
JS для обработки событий в форме заполнения шин
*/

function encode_params(object) {
    var encodedString = '';
    for (var prop in object) {
        if (object.hasOwnProperty(prop)) {
            if (encodedString.length > 0) {
                encodedString += '&';
            }
            encodedString += encodeURI(prop + '=' + object[prop]);
        }
    }
    return encodedString;
}

//При любом изменении параметров шины - пересчитываем рекомендованную цену
//Эта функция может использоваться как в шинах, так и в колесах, поэтому разная обработка
function change_tire(){
//            console.log(myResponse)
    var strDescription = document.getElementById('sezonnost').value + ' шины';
    var currPage=window.location.href.split("/").pop().split(".")[0]; //Определяем на какой мы странице
    var strTitle = (currPage === 'tire') ? ('Шины ') : (document.getElementById('title').value + ' '); //Если мы на wheel то title предзаполнено
    var strDescription = '';
    if (window.location.pathname.toLowerCase().includes('tire')){
        brandObject = document.getElementById('brand');
        modelObject = document.getElementById('model');
    } else
    {
        brandObject = document.getElementById('tirebrand');
        modelObject = document.getElementById('tiremodel');
    }

    if (!brandObject.options[brandObject.selectedIndex].label.includes('Выберите')) {
        strTitle = strTitle + ' ' + brandObject.options[brandObject.selectedIndex].label;
//        strDescription = strDescription + ' ' + brandObject.options[brandObject.selectedIndex].label;
    }
    if (modelObject.value){
        if (!modelObject.options[modelObject.selectedIndex].label.includes('Выберите')) {
            strTitle = strTitle + ' ' + modelObject.options[modelObject.selectedIndex].label;
//            strDescription = strDescription + ' ' + modelObject.options[modelObject.selectedIndex].label;
        }
    }
    if (document.getElementById('shirina_profilya').value) {
        strTitle = strTitle + ' ' + document.getElementById('shirina_profilya').value;
//        strDescription = strDescription + ' ' + document.getElementById('shirina_profilya').value;
    }
    if (document.getElementById('vysota_profilya').value) {
        strTitle = strTitle + '/' + document.getElementById('vysota_profilya').value;
//        strDescription = strDescription + '/' + document.getElementById('vysota_profilya').value;
    }
    var elementName = (currPage === 'tire') ? ('diametr') : ('rimdiametr');
    if (document.getElementById(elementName).value) {
        strTitle = strTitle + 'R' + document.getElementById(elementName).value;
//        strDescription = strDescription + 'R' + document.getElementById(elementName).value;
    }
//    if (document.getElementById('tire_purpose').value) {  // Это применимость
//        strDescription = strDescription + ' ' + document.getElementById('tire_purpose').value;
//    }
    strDescription = strTitle;
    if (document.getElementById('protector_height').value) {
        strDescription = strDescription + ', высота протектора ' + document.getElementById('protector_height').value + ' мм';
    }
    if (document.getElementById('protector_wear').value) {
        strDescription = strDescription + ', износ примерно ' + document.getElementById('protector_wear').value + '%';
    }
    document.getElementById('title').value = strTitle;
    if (currPage === 'tire') {
        document.getElementById('description').value = strDescription;
    } else
    {change_rim();}  //Обновляем параметры шин в колесе

}

//При любом изменении параметров диска - пересчитываем рекомендованную цену
function change_rim(){
    var xhr = new XMLHttpRequest();
    var beforeSend = function(xhr) {
        var csrf_token = document.querySelector('meta[name=csrf-token]').content;
        xhr.setRequestHeader("X-CSRFToken", csrf_token);
    };
    xhr.open('post', 'load_rim_prix');
    xhr.onload = function() {
        if (this.readyState === 4 && this.status === 200) {
            myResponse = JSON.parse(xhr.responseText)
            document.getElementById('recommended_price').value = myResponse.rim_price;
            if (document.getElementById('rimmodel').selectedIndex===-1) {
                model='';
            }
            else {
                model = document.getElementById('rimmodel').options[document.getElementById('rimmodel').selectedIndex].label;
            }
//            console.log(JSON.parse(xhr.responseText));
            if (window.location.pathname.toLowerCase().includes('rim')){
                document.getElementById('title').value= document.getElementById('rimtype').value + ' диски ' + document.getElementById('rimbrand').options[document.getElementById('rimbrand').selectedIndex].label + ' ' +
                model + ' ' +  rimwidth.value + 'R' + rimdiametr.value + ' ' + rimbolts.value + 'х' + rimboltsdiametr.value + ' ET ' + rimoffset.value ;
                document.getElementById('description').value= document.getElementById('rimtype').value + ' диски: \n Бренд ' + document.getElementById('rimbrand').options[document.getElementById('rimbrand').selectedIndex].label +
                '; \n Модель ' + model + '; \n ' +
                    'Ширина: ' + rimwidth.value + ', Диаметр: ' + rimdiametr.value + ' \n Сверловка: ' + rimbolts.value + 'х' + rimboltsdiametr.value + '\n Вылет: ' + rimoffset.value +
                    '\n Год производства: ' + rimyear.value + ' \n Состояние: ';
            } else  //wheel
            {
                document.getElementById('title').value='Колеса: \n' +  document.getElementById('rimtype').value + ' диски ' + document.getElementById('rimbrand').options[document.getElementById('rimbrand').selectedIndex].label + ' ' +
                model + ' ' +  rimwidth.value + 'R' + rimdiametr.value + ' ' + rimbolts.value + 'х' + rimboltsdiametr.value + ' ET ' + rimoffset.value ;
                document.getElementById('description').value= document.getElementById('rimtype').value + ' диски: \n Бренд ' + document.getElementById('rimbrand').options[document.getElementById('rimbrand').selectedIndex].label +
                '; \n Модель ' + model + '; \n ' +
                    'Ширина: ' + rimwidth.value + ', Диаметр: ' + rimdiametr.value + ' \n Сверловка: ' + rimbolts.value + 'х' + rimboltsdiametr.value + '\n Вылет: ' + rimoffset.value +
                    '\n Год производства: ' + rimyear.value + ' \n Состояние: \n' +
                    document.getElementById('sezonnost').value + ' шины: ' + document.getElementById('tirebrand').options[document.getElementById('tirebrand').selectedIndex].label + ' ' +
                    document.getElementById('tiremodel').options[document.getElementById('tiremodel').selectedIndex].label + ' ' +
                    document.getElementById('shirina_profilya').value + '/' + document.getElementById('vysota_profilya').value + 'R' + rimdiametr.value + '\n' +
                    'год выпуска: ' + tireproduct_year.value + '\n' +
                    'износ:' + protector_wear.value + '%';
            }
            document.getElementById('description').rows=8;

        }
        else if (xhr.status !== 200) {
            document.getElementById('recommended_price').value='0'
        }
    };
    beforeSend(xhr);
    xhr.setRequestHeader("Content-Type", "application/json;charset=UTF-8");
    try{
        var brand= document.getElementById('rimbrand').options[document.getElementById('rimbrand').selectedIndex].label;
        }
        catch(e){
            if (e instanceof TypeError) var brand='';
        }
    try{
        var model= document.getElementById('rimmodel').options[document.getElementById('rimmodel').selectedIndex].label;
        }
        catch(e){
            if (e instanceof TypeError) var model='';
        }
//    console.log('Оригинал=' + document.getElementById('rim_original').checked);
    xhr.send(JSON.stringify({
        'brand': brand,
        'model': model,
        'original': document.getElementById('rim_original').checked,
        'diametr': document.getElementById('rimdiametr').value,
        'width': document.getElementById('rimwidth').value,
        'ET' : document.getElementById('rimoffset').value,
        'bolts' : document.getElementById('rimbolts').value,
        'dia' : document.getElementById('rimboltsdiametr').value,
        'qte' : document.getElementById('qte').value,
        'rimyear': document.getElementById('rimyear').value
        }));
}

//Событие смены бренда шины на странице шин
if (document.getElementById('brand')) {
    document.getElementById('brand').addEventListener('change', function () {
//    ПРи смене бренда надо заполнить список моделей
    var element = document.getElementById('brand');
    var xhr = new XMLHttpRequest();
    xhr.open('post', 'changeBrandRequest');
    xhr.onload = function() {
        if (this.readyState === 4 && this.status === 200) {
            var modelElement = document.getElementById('model');
            var myResponse = JSON.parse(xhr.responseText);
            while (modelElement.options.length > 0) { //Чистим список
                modelElement.remove(0);
            }
            var option=document.createElement('option'); //Теперь заполняем
            option.text="Выберите модель";
            option.value=-1;
            modelElement.add(option, null);
            for (var i = 0; i < myResponse.length; i++) {
                var object = myResponse[i];
                var option=document.createElement('option'); //Теперь заполняем
                option.text=object.model;
                option.value=object.id;
                modelElement.add(option, null);
            }
            updateChart(0, 10)
        }
        else if (xhr.status !== 200) {
        }
    };
    var csrf_token = document.querySelector('meta[name=csrf-token]').content;
    xhr.setRequestHeader("X-CSRFToken", csrf_token);
    xhr.setRequestHeader("Content-Type", "application/json;charset=UTF-8");
    xhr.send(JSON.stringify({
        'brand': element.options[element.selectedIndex].label }));

    change_tire()
    });
}

//Событие смены бренда шины на странице колес
if (document.getElementById('tirebrand')) {
    document.getElementById('tirebrand').addEventListener('change', function () {
//    ПРи смене бренда надо заполнить список моделей
    var element = document.getElementById('tirebrand');
    var xhr = new XMLHttpRequest();
    xhr.open('post', 'changeBrandRequest');
    xhr.onload = function() {
        if (this.readyState === 4 && this.status === 200) {
            var modelElement = document.getElementById('tiremodel');
            var myResponse = JSON.parse(xhr.responseText);
            while (modelElement.options.length > 0) { //Чистим список
                modelElement.remove(0);
            }
            var option=document.createElement('option'); //Теперь заполняем
            option.text="Выберите модель";
            option.value=-1;
            modelElement.add(option, null);
            for (var i = 0; i < myResponse.length; i++) {
                var object = myResponse[i];
                var option=document.createElement('option'); //Теперь заполняем
                option.text=object.model;
                option.value=object.id;
                modelElement.add(option, null);
            }
//            updateChart(0, 10) - на странице колес пока нет графика
        }
        else if (xhr.status !== 200) {
        }
    };
    var csrf_token = document.querySelector('meta[name=csrf-token]').content;
    xhr.setRequestHeader("X-CSRFToken", csrf_token);
    xhr.setRequestHeader("Content-Type", "application/json;charset=UTF-8");
    xhr.send(JSON.stringify({
        'brand': element.options[element.selectedIndex].label }));

//    change_tire()
    });
}

//Событие смены бренда авто
if (document.getElementById('carbrand')) {
    document.getElementById('carbrand').addEventListener('change', function () {
//    ПРи смене бренда надо заполнить список моделей
    var element = document.getElementById('carbrand');
    var xhr = new XMLHttpRequest();
    xhr.open('post', 'changeCarBrandRequest');
    xhr.onload = function() {
        if (this.readyState === 4 && this.status === 200) {
            var modelElement = document.getElementById('carmodel');
            var myResponse = JSON.parse(xhr.responseText);
            while (modelElement.options.length > 0) { //Чистим список
                modelElement.remove(0);
            }
            var option=document.createElement('option'); //Теперь заполняем
            option.text="Выберите модель";
            option.value=-1;
            modelElement.add(option, null);
            for (var i = 0; i < myResponse.length; i++) {
                var object = myResponse[i];
                var option=document.createElement('option'); //Теперь заполняем
                option.text=object.model;
                option.value=object.id;
                modelElement.add(option, null);
            }
            change_rim();
        }
        else if (xhr.status !== 200) {
        }
    };
    var csrf_token = document.querySelector('meta[name=csrf-token]').content;
    xhr.setRequestHeader("X-CSRFToken", csrf_token);
    xhr.setRequestHeader("Content-Type", "application/json;charset=UTF-8");
    xhr.send(JSON.stringify({
        'carBrand': element.options[element.selectedIndex].label }));

    });
}

//Кнопка ведущая на список предложений на Авито
if (document.getElementById('AvitoTires')) {
    document.getElementById('AvitoTires').addEventListener('click', function () {
    var link='avito_tires/1?';
    if (document.getElementById('diametr').value){
        link= link + 'diametr=' + document.getElementById('diametr').value;
    }
    if (document.getElementById('shirina_profilya').value){
        link= link + '&width=' + document.getElementById('shirina_profilya').value ;
    }
    if (document.getElementById('vysota_profilya').value){
        link= link + '&height=' + document.getElementById('vysota_profilya').value ;
    }
    console.log(document.getElementById('display_area1').value)
    if (document.getElementById('display_area1').options[document.getElementById('display_area1').selectedIndex].label){
        link= link + '&region=' + document.getElementById('display_area1').options[document.getElementById('display_area1').selectedIndex].label ;
    }
    window.open(link, '_self');  //, '_blank'
    });
}

//Событие смены бренда диска
if (document.getElementById('rimbrand')) {
    document.getElementById('rimbrand').addEventListener('change', function () {
//    ПРи смене бренда надо заполнить список моделей
    var element = document.getElementById('rimbrand');
    var xhr = new XMLHttpRequest();
    xhr.open('post', 'changeRimBrandRequest');
    xhr.onload = function() {
        if (this.readyState === 4 && this.status === 200) {
            var modelElement = document.getElementById('rimmodel');
            var myResponse = JSON.parse(xhr.responseText);
            while (modelElement.options.length > 0) { //Чистим список
                modelElement.remove(0);
            }
            var option=document.createElement('option'); //Теперь заполняем
            option.text="Выберите модель";
            option.value=-1;
            modelElement.add(option, null);
            for (var i = 0; i < myResponse.length; i++) {
                var object = myResponse[i];
                var option=document.createElement('option'); //Теперь заполняем
                option.text=object.model;
                option.value=object.id;
                modelElement.add(option, null);
            }
            change_rim();
        }
        else if (xhr.status !== 200) {
        }
    };
    var csrf_token = document.querySelector('meta[name=csrf-token]').content;
    xhr.setRequestHeader("X-CSRFToken", csrf_token);
    xhr.setRequestHeader("Content-Type", "application/json;charset=UTF-8");
    xhr.send(JSON.stringify({
        'brand': element.options[element.selectedIndex].label }));

    });
}

//Событие смены модели шин
if (document.getElementById('model')) {
    document.getElementById('model').addEventListener('change', function () {
    var element = document.getElementById('model');
    var xhr = new XMLHttpRequest();
    xhr.open('post', 'changeModelRequest');
    xhr.onload = function() {
        if (this.readyState === 4 && this.status === 200) {
            var seasonElement = document.getElementById('sezonnost');
            var myResponse = JSON.parse(xhr.responseText);
            var season = myResponse.season;
//            console.log(element.data)
            document.getElementById('tire_purpose').value=myResponse.purpose
            document.getElementById('tire_description').value=myResponse.description
            for (var i = 0; i < seasonElement.length; i++) {
//                console.log(seasonElement.options[i].value);
                var categ_value=seasonElement.options[i].value;
                if (categ_value===season) {
                    seasonElement.value=categ_value;
                }
            }
        }
        else if (xhr.status !== 200) {
        }
    };
    var csrf_token = document.querySelector('meta[name=csrf-token]').content;
    xhr.setRequestHeader("X-CSRFToken", csrf_token);
    xhr.setRequestHeader("Content-Type", "application/json;charset=UTF-8");
    var brand=document.getElementById('brand').options[document.getElementById('brand').selectedIndex].label;
    var model=document.getElementById('model').options[document.getElementById('model').selectedIndex].label;
//    console.log('brand, model='+brand + ' ' + model);
    xhr.send(JSON.stringify({
        'brand': brand,
        'model': model }));
    change_tire()
    });
}


//Событие смены параметров шин в фильтрах StockTable
function stockTableFilters(){
    var xhr = new XMLHttpRequest();
    xhr.open('post', 'stock_tables');
    xhr.onload = function() {
        if (this.readyState === 4 && this.status === 200) {
            result = JSON.parse(xhr.responseText);
            window.location.href = result.link;
//            console.log(result);
        }
        else if (xhr.status !== 200) {
        }
    };
    var csrf_token = document.querySelector('meta[name=csrf-token]').content;
    xhr.setRequestHeader("X-CSRFToken", csrf_token);
    xhr.setRequestHeader("Content-Type", "application/json;charset=UTF-8");
    var brand=document.getElementById('stockTableBrand').options[document.getElementById('stockTableBrand').selectedIndex].label;
    xhr.send(JSON.stringify({
        'brand': brand,
        'diametr': document.getElementById('stockTablediametr').options[document.getElementById('stockTablediametr').selectedIndex].label,
        'width': document.getElementById('stockTablewidth').options[document.getElementById('stockTablewidth').selectedIndex].label,
        'height': document.getElementById('stockTableheight').options[document.getElementById('stockTableheight').selectedIndex].label}));
}

if (document.getElementById('stockTableBrand')) {
    document.getElementById('stockTableBrand').addEventListener('change', function () {stockTableFilters(); });
}

if (document.getElementById('stockTablediametr')) {
    document.getElementById('stockTablediametr').addEventListener('change', function () {stockTableFilters(); });
}

if (document.getElementById('stockTablewidth')) {
    document.getElementById('stockTablewidth').addEventListener('change', function () {stockTableFilters(); });
}
if (document.getElementById('stockTableheight')) {
    document.getElementById('stockTableheight').addEventListener('change', function () {stockTableFilters(); });
}

//Событие смены модели машины
if (document.getElementById('carmodel')) {
    document.getElementById('carmodel').addEventListener('change', function () {
    var element = document.getElementById('carmodel');
    var xhr = new XMLHttpRequest();
    xhr.open('post', 'changeCarModelRequest');
    xhr.onload = function() {
        if (this.readyState === 4 && this.status === 200) {
            var myResponse = JSON.parse(xhr.responseText);
//            Заменим бренд и модель на бренд АМ
            if (document.getElementById('rim_original').checked === true) {
                while (rimbrand.options.length > 0) { //Чистим список
                    rimbrand.remove(0);
                }
                var option=document.createElement('option'); //Теперь заполняем
                option.text=myResponse.brand;
                document.getElementById('rimbrand').add(option, null);
                document.getElementById('rimbrand').value=myResponse.brand;
                while (rimmodel.options.length > 0) { //Чистим список
                    rimmodel.remove(0);
                }
                var option=document.createElement('option'); //Теперь заполняем
                option.text=myResponse.model;
                document.getElementById('rimmodel').add(option, null);
                document.getElementById('rimmodel').value=myResponse.model;
            }

            for (var i = 0; i < myResponse.length; i++) {
                var object = myResponse[i];
                var option=document.createElement('option'); //Теперь заполняем
                option.text=object.model;
                option.value=object.id;
                modelElement.add(option, null);
            }
            document.getElementById('rimoffset').value=myResponse.ET;
            document.getElementById('rimdiametr').value=myResponse.rimDiametr;
            document.getElementById('rimwidth').value=myResponse.rimWidth;
            document.getElementById('rimbolts').value=myResponse.rimBolts;
            document.getElementById('rimboltsdiametr').value=myResponse.rimDia;
            change_rim();
        }
        else if (xhr.status !== 200) {
        }
    };
    var csrf_token = document.querySelector('meta[name=csrf-token]').content;
    xhr.setRequestHeader("X-CSRFToken", csrf_token);
    xhr.setRequestHeader("Content-Type", "application/json;charset=UTF-8");
    var brand=document.getElementById('carbrand').options[document.getElementById('carbrand').selectedIndex].label;
    var model=document.getElementById('carmodel').options[document.getElementById('carmodel').selectedIndex].label;
//    console.log('brand, model='+brand + ' ' + model);
    xhr.send(JSON.stringify({
        'brand': brand,
        'model': model }));
//    change_carModel()
    });
}

//Событие выбора оригинальных дисков
if (document.getElementById('rim_original')) {
    document.getElementById('rim_original').addEventListener('change', function () {
    var element = document.getElementById('carmodel');
    var xhr = new XMLHttpRequest();
    xhr.open('post', 'changeCarModelRequest');
    rimBrand=document.getElementById('rimbrand');
    rimModel=document.getElementById('rimmodel');

    xhr.onload = function() {
        if (this.readyState === 4 && this.status === 200) {
            var myResponse = JSON.parse(xhr.responseText);
//            Заменим бренд и модель на бренд АМ
            if (document.getElementById('rim_original').checked === true) {
                while (rimBrand.options.length > 0) { //Чистим список
                    rimBrand.remove(0);
                }
                var option=document.createElement('option'); //Теперь заполняем
                option.text=myResponse.brand;
                option.value=myResponse.brand;
                option.setAttribute('selected', '');
                rimBrand.add(option, null);
                while (rimModel.options.length > 0) { //Чистим список
                    rimModel.remove(0);
                }
                var option=document.createElement('option'); //Теперь заполняем
                option.text=myResponse.model;
                option.value=myResponse.model;
                option.setAttribute('selected', '');
                rimModel.add(option, null);
                rimModel.value=myResponse.model;
            } else {
                fillBrandAndModelDefaults();
            }

            for (var i = 0; i < myResponse.length; i++) {
                var object = myResponse[i];
                var option=document.createElement('option'); //Теперь заполняем
                option.text=object.model;
                option.value=object.id;
                modelElement.add(option, null);
            }
            document.getElementById('rimoffset').value=myResponse.ET;
            document.getElementById('rimdiametr').value=myResponse.rimDiametr;
            document.getElementById('rimwidth').value=myResponse.rimWidth;
            document.getElementById('rimbolts').value=myResponse.rimBolts;
            document.getElementById('rimboltsdiametr').value=myResponse.rimDia;
            change_rim();
        }
        else if (xhr.status !== 200) {
        }
    };
    var csrf_token = document.querySelector('meta[name=csrf-token]').content;
    xhr.setRequestHeader("X-CSRFToken", csrf_token);
    xhr.setRequestHeader("Content-Type", "application/json;charset=UTF-8");
    try{
        var brand= document.getElementById('carbrand').options[document.getElementById('carbrand').selectedIndex].label;
        }
        catch(e){
            if (e instanceof TypeError) var brand='';
        }
    try{
        var model= document.getElementById('carmodel').options[document.getElementById('carmodel').selectedIndex].label;
        }
        catch(e){
            if (e instanceof TypeError) var model='';
        }
//    var brand=document.getElementById('carBrand').options[document.getElementById('carBrand').selectedIndex].label;
//    var model=document.getElementById('carModel').options[document.getElementById('carModel').selectedIndex].label;
//    console.log('brand, model='+brand + ' ' + model);
    xhr.send(JSON.stringify({
        'brand': brand,
        'model': model }));
//    change_carModel()
    });
}

function fillBrandAndModelDefaults(){
/*отправляем на сервер сообщение с id элемента, который надо поменять*/
    var xhr = new XMLHttpRequest();
    xhr.open('post', 'change_original_state');

    xhr.onload = function() {
        if (this.readyState === 4 && this.status === 200) {
            var myResponse = JSON.parse(xhr.responseText);
//            Заменим бренд и модель на бренд АМ
            if (document.getElementById('rim_original').checked === false) {
                while (rimbrand.options.length > 0) { //Чистим список
                    rimbrand.remove(0);
                }
                for (var i = 0; i < myResponse.length; i++) {
                    var object = myResponse[i];
                    var option=document.createElement('option'); //Теперь заполняем
                    option.text=object.brand;
                    option.value=object.id;
                    rimbrand.add(option, null);
                }
                while (rimmodel.options.length > 0) { //Чистим список
                    rimmodel.remove(0);
                }
            }
            change_rim();
        }
        else if (xhr.status !== 200) {
//            document.getElementById('recommended_price').value='0'
        }
    };
    var csrf_token = document.querySelector('meta[name=csrf-token]').content;
    xhr.setRequestHeader("X-CSRFToken", csrf_token);
    xhr.setRequestHeader("Content-Type", "application/json;charset=UTF-8");
//    console.log(element.checked)
    xhr.send();
}

if (document.getElementById('diametr')) {
    document.getElementById('diametr').addEventListener('change', function () {
    change_tire();
    });
}

if (document.getElementById('rimmodel')) {
    document.getElementById('rimmodel').addEventListener('change', function () {
    change_rim();
    });
}

if (document.getElementById('rimdiametr')) {
    document.getElementById('rimdiametr').addEventListener('change', function () {
    change_rim();
    });
}

if (document.getElementById('shirina_profilya')) {
    document.getElementById('shirina_profilya').addEventListener('change', function () {
    change_tire();
    });
}

if (document.getElementById('rimwidth')) {
    document.getElementById('rimwidth').addEventListener('change', function () {
    change_rim();
    });
}

if (document.getElementById('rimyear')) {
    document.getElementById('rimyear').addEventListener('change', function () {
    change_rim();
    });
}

if (document.getElementById('vysota_profilya')) {
    document.getElementById('vysota_profilya').addEventListener('change', function () {
    change_tire();
    });
}

if (document.getElementById('rimbolts')) {
    document.getElementById('rimbolts').addEventListener('change', function () {
    change_rim();
    });
}

if (document.getElementById('protector_height')) {
    document.getElementById('protector_height').addEventListener('change', function () {
    change_tire();
    });
}
if (document.getElementById('protector_wear')) {
    document.getElementById('protector_wear').addEventListener('change', function () {
    change_tire();
    });
}

if (document.getElementById('sezonnost')) {
    document.getElementById('sezonnost').addEventListener('change', function () {
    change_tire();
    });
}


if (document.getElementById('rimboltsdiametr')) {
    document.getElementById('rimboltsdiametr').addEventListener('change', function () {
    change_rim();
    });
}

if (document.getElementById('qte')) {
    document.getElementById('qte').addEventListener('change', function () {
    updateRecommendedPrice();
    if (window.location.pathname.toLowerCase().includes('rim') || window.location.pathname.toLowerCase().includes('wheel')) { change_rim();}
    if (window.location.pathname.toLowerCase().includes('tire')){change_tire();}
    });
}

if (document.getElementById('inSet')) {
    document.getElementById('inSet').addEventListener('change', function () {
    updateRecommendedPrice();
    if (window.location.pathname.toLowerCase().includes('rim') || window.location.pathname.toLowerCase().includes('wheel')) { change_rim();}
    if (window.location.pathname.toLowerCase().includes('tire')){change_tire();}
    });
}

/*   Функция меняет статус элемента с Опубликовано на обратно */
function change_publishedstatus(id) {
    var element = document.getElementById(id);
/*отправляем на сервер сообщение с id элемента, который надо поменять*/
    var xhr = new XMLHttpRequest();
    xhr.open('post', 'change_tire_state');

    xhr.onload = function() {
        if (this.readyState === 4 && this.status === 200) {
            if (JSON.parse(xhr.responseText)['sold'] === true) {
                var curr_id = JSON.parse(xhr.responseText)['id'];
            //Все площадки этой записи ставим в False
                document.getElementById('idAvito_' + curr_id).checked = false;
                document.getElementById('idYoula_' + curr_id).checked = false;
                document.getElementById('idDrom_' + curr_id).checked = false;
            }
        }
        else if (xhr.status !== 200) {
//            document.getElementById('recommended_price').value='0'
        }
    };
    var csrf_token = document.querySelector('meta[name=csrf-token]').content;
    xhr.setRequestHeader("X-CSRFToken", csrf_token);
    xhr.setRequestHeader("Content-Type", "application/json;charset=UTF-8");
//    console.log(element.checked)
    xhr.send(JSON.stringify({
        'id': id,
        'value': element.checked }));
}

/*   Функция меняет статус продвижения на Авито */
function change_promostatus(id) {
    var element = document.getElementById(id);
/*отправляем на сервер сообщение с id элемента, который надо поменять*/
    var xhr = new XMLHttpRequest();
    xhr.open('post', 'change_promo_state');
    xhr.onload = function() {
        if (this.readyState === 4 && this.status === 200) {
        }
        else if (xhr.status !== 200) {
        }
    };
    var csrf_token = document.querySelector('meta[name=csrf-token]').content;
    xhr.setRequestHeader("X-CSRFToken", csrf_token);
    xhr.setRequestHeader("Content-Type", "application/json;charset=UTF-8");
    xhr.send(JSON.stringify({
        'id': id,
        'value': element.checked }));
}

/*   Функция меняет статус продвижения на Авто.ру */
function change_avtoru_promo(id) {
    var element = document.getElementById(id);
/*отправляем на сервер сообщение с id элемента, который надо поменять*/
    var xhr = new XMLHttpRequest();
    xhr.open('post', 'change_avtorupromo_state');
    xhr.onload = function() {
        if (this.readyState === 4 && this.status === 200) {

        }
        else if (xhr.status !== 200) {

        }
    };
    var csrf_token = document.querySelector('meta[name=csrf-token]').content;
    xhr.setRequestHeader("X-CSRFToken", csrf_token);
    xhr.setRequestHeader("Content-Type", "application/json;charset=UTF-8");
    xhr.send(JSON.stringify({
        'id': id,
        'value': element.checked }));
}

if (document.getElementById('personalPhotoFile')) {
    document.getElementById('personalPhotoFile').addEventListener('change', handlePersonalPhoto, false);
}

function handlePersonalPhoto() {
    var xhr = new XMLHttpRequest();
    xhr.open('post', 'save_personnal_photo', true);
    const fd = new FormData();
    fd.append('persoPhoto', this.files[0]);
    xhr.onload = function() {
        if (this.readyState === 4 && this.status === 200) {
            document.getElementById("personalPhoto").src = JSON.parse(xhr.responseText)['result'];
            document.getElementById("avatar").src = JSON.parse(xhr.responseText)['result'];
            document.getElementById("nav_avatar").src = JSON.parse(xhr.responseText)['result'];

        }
        else if (xhr.status !== 200) {
        }
    };
    var csrf_token = document.querySelector('meta[name=csrf-token]').content;
    xhr.setRequestHeader("X-CSRFToken", csrf_token);
    xhr.send(fd);
}


//При изменении глубины протектора надо менять износ
if (document.getElementById('protector_height')) {
    document.getElementById('protector_height').addEventListener('change', function () {
    var element = document.getElementById('protector_height');
    var currPage=window.location.href.split("/").pop().split(".")[0]; //Определяем на какой мы странице

    var xhr = new XMLHttpRequest();
    xhr.open('post', 'updateWear');
    xhr.onload = function() {
        if (this.readyState === 4 && this.status === 200) {
//            var graphs = JSON.parse(xhr.response);
//            console.log(graphs)
//            Plotly.newPlot('chart',graphs,{});
            document.getElementById('protector_wear').value=xhr.response;
            change_tire();
            if (currPage==="tire"){
                updateChart(0, 10);
            }
        }
        else if (xhr.status !== 200) {
        }
    };
    var csrf_token = document.querySelector('meta[name=csrf-token]').content;
    xhr.setRequestHeader("X-CSRFToken", csrf_token);
    xhr.setRequestHeader("Content-Type", "application/json;charset=UTF-8");

    var elementName = (currPage === 'tire') ? ('diametr') : ('rimdiametr'); //В зависимости от страницы разные названия поля диаметр
    xhr.send(JSON.stringify({'region': document.getElementById('display_area1').options[document.getElementById('display_area1').selectedIndex].label,
        'protector_height':document.getElementById('protector_height').value,
        'season':document.getElementById('sezonnost').options[document.getElementById('sezonnost').selectedIndex].label,
        'width':document.getElementById('shirina_profilya').options[document.getElementById('shirina_profilya').selectedIndex].label,
        'height':document.getElementById('vysota_profilya').options[document.getElementById('vysota_profilya').selectedIndex].label,
        'diametr':document.getElementById(elementName).options[document.getElementById(elementName).selectedIndex].label, 'pages':10}));
    });
}

function updateRecommendedPrice(){
    if (document.getElementById('recommended_Unitprice').value) {
        document.getElementById('recommended_price').value = parseInt(document.getElementById('recommended_Unitprice').value) * document.getElementById('qte').value * document.getElementById('inSet').value;
        }
}

//Событие нажатия кнопки Обновить
if (document.getElementById('Refresh')) {
    document.getElementById('Refresh').addEventListener('click', function(){updateChart(0, 10)}, false);}

if (document.getElementById('protector_wear')) {
    document.getElementById('protector_wear').addEventListener('change', function(){updateChart(0, 10)}, false);}

//Событие нажатия кнопки Скан предложений Авито
if (document.getElementById('StartAvitoSearch')) {
    document.getElementById('StartAvitoSearch').addEventListener('click', function () {
//    При смене региона надо перерисовать график
    var pages = 10;
    var xhr = new XMLHttpRequest();
    xhr.open('post', 'start_avitoscan');
    xhr.onload = function() {
        if (this.readyState === 4 && this.status === 202) {
//            console.log(xhr.getResponseHeader('Location'));
            update_avitodata(xhr.getResponseHeader('Location'));
        }
        else if (xhr.status !== 200 && xhr.status !== 202){
        }
    };
    var csrf_token = document.querySelector('meta[name=csrf-token]').content;
    xhr.setRequestHeader("X-CSRFToken", csrf_token);
    xhr.setRequestHeader("Content-Type", "application/json;charset=UTF-8");
//    console.log(document.getElementById('display_area1').options[document.getElementById('display_area1').selectedIndex].label)
    xhr.send(JSON.stringify({'diametr': document.getElementById('diametr').options[document.getElementById('diametr').selectedIndex].label,
        'width':document.getElementById('width').value,
        'height':document.getElementById('height').value,
        'lon':document.getElementById('searchLon').value,
        'lat':document.getElementById('searchLat').value,
        'region':document.getElementById('searchRegion').options[document.getElementById('searchRegion').selectedIndex].label,
        'season':document.getElementById('sezonnost').options[document.getElementById('sezonnost').selectedIndex].label,
        'pages':document.getElementById('pages').value,
        'searchRadius':document.getElementById('searchRadius').value}));
    });
}

function update_spinner(){
    var spinner = document.getElementById('AVITO_STATUS');
    spinner.innerHTML = spinner.innerHTML === '.' ? '..' :
        (spinner.innerHTML === '..') ? '...' :
        (spinner.innerHTML === '...') ? '.' :
        '.';
}

function update_avitodata(status_url) {
    var xhr = new XMLHttpRequest();
    xhr.open('GET', status_url, true);
    xhr.onload = function() {
        if (this.readyState === 4 && this.status === 200) {
            data = JSON.parse(xhr.response);
//            console.log(data['state']);
            if (data['state'] === 'FINISHED' || data['state'] === 'SUCCESS'){
                document.getElementById('AVITO_STATUS').innerHTML = '';
            }

             if (data['state'] === 'PENDING' || data['state'] === 'PROGRESS') { //&& data['state'] != 'PROGRESS'
                    // rerun in 4 seconds
                    setTimeout(function() {
                        update_avitodata(status_url);
                    }, 4000);
//                    console.log(data['currPage'])
                    update_spinner();

                    if (data['currPage']!== null) {
                        document.getElementById('AVITO_STATUS').innerHTML = Math.round(parseInt(data['currPage']['page']) / parseInt(document.getElementById('pages').value) * 100.) + '%';
//                        console.log('Значение = ' + parseInt(data['currPage']['page']) / parseInt(document.getElementById('pages').value) * 100.);
                    }
             }
             if (data['state'] != 'PENDING' && data['state'] != 'SUCCESS'){
                if ('offerstable' in data) {
                    // show result
                    var myTable='';
                    myTable +='<table class="table table-flush table-striped  table-sm table-hover">';
                    myTable += '<thead class="thead-light">';
                    myTable += '<tr class="d-flex">';
                    for (var i=0; i< data['columnNames'].length; i++){  //Собираем заголовки таблицы
                        myTable += '<th class="col-sm-' + data['columnWidths'][i] +'">' + data['columnNames'][i] + '</th>';
                    };
                    myTable +='</tr> </thead>';
                    console.log('длина масива данных: ' + data['offerstable'].length)
                    for (var i=0; i< data['offerstable'].length; i++){  //Собираем значения таблицы
                        myTable += '<tr class="d-flex">';
                        for (var j=0;  j<data['columnWidths'].length; j++){
                            myTable += '<td class="col-sm-' + data['columnWidths'][j] + '">';
                            //
                            myTable += data['offerstable'][i][j] + '</td>';
                        };
                    };
                    document.getElementById("avito_table").innerHTML = myTable
                }
             }
        }
        else if (xhr.status !== 200 ){
        }

    };

    var csrf_token = document.querySelector('meta[name=csrf-token]').content;
    xhr.setRequestHeader("X-CSRFToken", csrf_token);
    xhr.setRequestHeader("Content-Type", "application/json;charset=UTF-8");
    xhr.send();
}

//Событие нажатия кнопки Найти предложения шин на Авито
if (document.getElementById('GetAvitoTirePrices')) {
    document.getElementById('GetAvitoTirePrices').addEventListener('click', function () {
//    При смене региона надо перерисовать график
    var pages = 3;
    var xhr = new XMLHttpRequest();
    xhr.open('post', 'start_TirePricesScan');
    xhr.onload = function() {
        if (this.readyState === 4 && this.status === 202) {
            update_tirePrices(xhr.getResponseHeader('Location'));
//            var graphs = JSON.parse(xhr.response);
//            Plotly.newPlot('chart',graphs,{});
        }
        else if (xhr.status !== 202) {
        }
    };
    var csrf_token = document.querySelector('meta[name=csrf-token]').content;
    xhr.setRequestHeader("X-CSRFToken", csrf_token);
    xhr.setRequestHeader("Content-Type", "application/json;charset=UTF-8");
//    console.log(document.getElementById('display_area1').options[document.getElementById('display_area1').selectedIndex].label)
    xhr.send(JSON.stringify({'region': document.getElementById('display_area1').options[document.getElementById('display_area1').selectedIndex].label,
        'drom_region': document.getElementById('drom_display_area').options[document.getElementById('drom_display_area').selectedIndex].label,
        'protector_wear':document.getElementById('protector_wear').value,
        'season':document.getElementById('sezonnost').options[document.getElementById('sezonnost').selectedIndex].label,
        'width':document.getElementById('shirina_profilya').options[document.getElementById('shirina_profilya').selectedIndex].label,
        'height':document.getElementById('vysota_profilya').options[document.getElementById('vysota_profilya').selectedIndex].label,
        'diametr':document.getElementById('diametr').options[document.getElementById('diametr').selectedIndex].label, 'pages':pages}));
    });
}

function update_tirePrices(status_url) {
    var xhr = new XMLHttpRequest();
//    console.log(status_url);
//    console.log(status_url);
    const task_id = status_url.split('?').join(',').split('=').join(',').split(',')[2];
    const hreflink = status_url.split('?')[0];
    xhr.open('POST', status_url);
    xhr.onload = function() {
        if (this.readyState === 4 && this.status === 200) {
            data = JSON.parse(xhr.response);
            if (data['state'] === 'FINISHED' || data['state'] === 'SUCCESS'){
                updateChart(data['currPage']['page'], data['currPage']['totalPages']);
                document.getElementById('AVITO_STATUS').innerHTML = 'Готово';
                document.getElementById('chart_progress_text').textContent = "100%"
                document.getElementById('chart_progress').setAttribute('aria-valuenow', 100);
                document.getElementById('chart_progress').style.width = "100%";
            }

             if (data['state'] === 'PENDING' || data['state'] === 'PROGRESS') { //&& data['state'] != 'PROGRESS'
                    // rerun in 4 seconds
                    setTimeout(function() {
                        update_tirePrices(status_url);
                    }, 3000);
                    update_spinner();
                    if (data['currPage']!== null) {
//                        console.log(data['currPage']);
                        updateChart(data['currPage']['page'], data['currPage']['totalPages']);
                    }
             }
//             if (data['state'] != 'PENDING' && data['state'] != 'SUCCESS'){
//                    update_spinner();
//                    if (data['currPage']!== null) {
//                        updateChart(data['currPage']['page'], data['currPage']['totalPages']);
//                    }
//             }
        }
        else if (xhr.status !== 200 ){
        }

    };

    var csrf_token = document.querySelector('meta[name=csrf-token]').content;
    xhr.setRequestHeader("X-CSRFToken", csrf_token);
    xhr.setRequestHeader("Content-Type", "application/json;charset=UTF-8");
//    console.log(document.getElementById('display_area1').options[document.getElementById('display_area1').selectedIndex].label)
    xhr.send(JSON.stringify({'task_id':task_id, 'region': document.getElementById('display_area1').options[document.getElementById('display_area1').selectedIndex].label,
        'protector_wear':document.getElementById('protector_wear').value,
        'season':document.getElementById('sezonnost').options[document.getElementById('sezonnost').selectedIndex].label,
        'width':document.getElementById('shirina_profilya').options[document.getElementById('shirina_profilya').selectedIndex].label,
        'height':document.getElementById('vysota_profilya').options[document.getElementById('vysota_profilya').selectedIndex].label,
        'diametr':document.getElementById('diametr').options[document.getElementById('diametr').selectedIndex].label}));
}


//Функция забирает параметры расчета и по ним строит график
function updateChart(nPage, nTotalPages){
    var pages=nTotalPages;
    var xhr = new XMLHttpRequest();
    xhr.open('post', 'updateChartNow');
    xhr.onload = function() {
        if (this.readyState === 4 && this.status === 200) {
//            console.log(graphs)
            var graphs = JSON.parse(JSON.parse(xhr.response)['chartData']);
            Plotly.newPlot('chart',graphs,{});
//            console.log(Math.round(100/nTotalPages*nPage));
            var progress = Math.round(100/nTotalPages*nPage);
            document.getElementById('chart_progress_text').textContent = progress + "%"
            document.getElementById('chart_progress').setAttribute('aria-valuenow', progress);
            document.getElementById('chart_progress').style.width = progress + "%";
            document.getElementById('recommended_price').value = JSON.parse(JSON.parse(xhr.response)['predictResult']) * document.getElementById('qte').value * document.getElementById('inSet').value;
            document.getElementById('recommended_Unitprice').value = JSON.parse(JSON.parse(xhr.response)['predictResult']);
        }
        else if (xhr.status !== 200) {
        }
    };
    var csrf_token = document.querySelector('meta[name=csrf-token]').content;
    xhr.setRequestHeader("X-CSRFToken", csrf_token);
    xhr.setRequestHeader("Content-Type", "application/json;charset=UTF-8");
//    console.log(document.getElementById('display_area1').options[document.getElementById('display_area1').selectedIndex].label)
    xhr.send(JSON.stringify({'region': document.getElementById('display_area1').options[document.getElementById('display_area1').selectedIndex].label,
        'protector_wear':document.getElementById('protector_wear').value,
        'brand':document.getElementById('brand').options[document.getElementById('brand').selectedIndex].label,
        'season':document.getElementById('sezonnost').options[document.getElementById('sezonnost').selectedIndex].label,
        'width':document.getElementById('shirina_profilya').options[document.getElementById('shirina_profilya').selectedIndex].label,
        'height':document.getElementById('vysota_profilya').options[document.getElementById('vysota_profilya').selectedIndex].label,
        'diametr':document.getElementById('diametr').options[document.getElementById('diametr').selectedIndex].label, 'pages':pages}));
}
