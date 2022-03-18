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
function change_tire(){
    var xhr = new XMLHttpRequest();
    var beforeSend = function(xhr) {
        var csrf_token = document.querySelector('meta[name=csrf-token]').content;
        xhr.setRequestHeader("X-CSRFToken", csrf_token);
    };
    xhr.open('post', 'load_tire_prix');
    xhr.onload = function() {
        if (this.readyState === 4 && this.status === 200) {
            myResponse = JSON.parse(xhr.responseText)
            document.getElementById('recommended_price').value = myResponse.tire_price;
            document.getElementById('tire_newprice').value = myResponse.newtire_price;
//            console.log(JSON.parse(xhr.responseText));
            document.getElementById('title').value= 'Шины ' + JSON.parse(xhr.responseText)['brand'] + ' ' + JSON.parse(xhr.responseText)['model'] + ' ' +
                JSON.parse(xhr.responseText)['size'] + 'R' + JSON.parse(xhr.responseText)['diametr'];
            document.getElementById('description').value= document.getElementById('sezonnost').value + ' ' + document.getElementById('condition').value + ' шины ' + JSON.parse(xhr.responseText)['brand'] + ' ' + JSON.parse(xhr.responseText)['model'] + ' ' +
                JSON.parse(xhr.responseText)['size'] + 'R' + JSON.parse(xhr.responseText)['diametr']  + ' ' + document.getElementById('tire_purpose').value +
                ', высота протектора ' + document.getElementById('protector_height').value + ' мм';
        }
        else if (xhr.status !== 200) {
            document.getElementById('recommended_price').value='0'
        }
    };
    beforeSend(xhr);
    xhr.setRequestHeader("Content-Type", "application/json;charset=UTF-8");
    var saisonality =  document.getElementById('sezonnost').value
    winter_coef = saisonality.includes('имние'); /*проверяем что шины зимние*/
    thorns_coef = saisonality.includes(' шипован');
    try{
        var brand= document.getElementById('brand').options[document.getElementById('brand').selectedIndex].label;
        }
        catch(e){
            if (e instanceof TypeError) var brand='';
        }
    try{
        var model= document.getElementById('model').options[document.getElementById('model').selectedIndex].label;
        }
        catch(e){
            if (e instanceof TypeError) var model='';
        }
//    console.log('model='+model);
    xhr.send(JSON.stringify({
        'brand': brand,
        'model': model,
        'diametr': document.getElementById('diametr').value,
        'size': document.getElementById('shirina_profilya').value + "/" + document.getElementById('vysota_profilya').value,
        'thorns' : thorns_coef,
        'winter_coef': winter_coef,
        'protector_height': document.getElementById('protector_height').value,
        'qte' : document.getElementById('qte').value
        }));
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
            document.getElementById('title').value= document.getElementById('rimtype').value + ' диски ' + document.getElementById('rimbrand').options[document.getElementById('rimbrand').selectedIndex].label + ' ' +
            model + ' ' +  rimwidth.value + 'R' + rimdiametr.value + ' ' + rimbolts.value + 'х' + rimboltsdiametr.value + ' ET ' + rimoffset.value ;
            document.getElementById('description').value= document.getElementById('rimtype').value + ' диски: \n Бренд ' + document.getElementById('rimbrand').options[document.getElementById('rimbrand').selectedIndex].label +
            '; \n Модель ' + model + '; \n ' +
                'Ширина: ' + rimwidth.value + ', Диаметр: ' + rimdiametr.value + ' \n Сверловка: ' + rimbolts.value + 'х' + rimboltsdiametr.value + '\n Вылет: ' + rimoffset.value +
                '\n Год производства: ' + rimyear.value + ' \n Состояние: ';
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
        'qte' : document.getElementById('rimqte').value,
        'rimyear': document.getElementById('rimyear').value
        }));
}

//Событие смены бренда шины
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

//Событие смены бренда авто
if (document.getElementById('carBrand')) {
    document.getElementById('carBrand').addEventListener('change', function () {
//    ПРи смене бренда надо заполнить список моделей
    var element = document.getElementById('carBrand');
    var xhr = new XMLHttpRequest();
    xhr.open('post', 'changeCarBrandRequest');
    xhr.onload = function() {
        if (this.readyState === 4 && this.status === 200) {
            var modelElement = document.getElementById('carModel');
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

//Событие смены модели машины
if (document.getElementById('carModel')) {
    document.getElementById('carModel').addEventListener('change', function () {
    var element = document.getElementById('carModel');
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
    var brand=document.getElementById('carBrand').options[document.getElementById('carBrand').selectedIndex].label;
    var model=document.getElementById('carModel').options[document.getElementById('carModel').selectedIndex].label;
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
    var element = document.getElementById('carModel');
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
                rimBrand.add(option, null);
                rimBrand.value=myResponse.brand;
                while (rimModel.options.length > 0) { //Чистим список
                    rimModel.remove(0);
                }
                var option=document.createElement('option'); //Теперь заполняем
                option.text=myResponse.model;
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
        var brand= document.getElementById('carBrand').options[document.getElementById('carBrand').selectedIndex].label;
        }
        catch(e){
            if (e instanceof TypeError) var brand='';
        }
    try{
        var model= document.getElementById('carModel').options[document.getElementById('carModel').selectedIndex].label;
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

if (document.getElementById('rimboltsdiametr')) {
    document.getElementById('rimboltsdiametr').addEventListener('change', function () {
    change_rim();
    });
}

if (document.getElementById('rimqte')) {
    document.getElementById('rimqte').addEventListener('change', function () {
    change_rim();
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
                document.getElementById('idAvtoru_' + curr_id).checked = false;
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
    var xhr = new XMLHttpRequest();
    xhr.open('post', 'updateWear');
    xhr.onload = function() {
        if (this.readyState === 4 && this.status === 200) {
//            var graphs = JSON.parse(xhr.response);
//            console.log(graphs)
//            Plotly.newPlot('chart',graphs,{});
            document.getElementById('protector_wear').value=xhr.response
        }
        else if (xhr.status !== 200) {
        }
    };
    var csrf_token = document.querySelector('meta[name=csrf-token]').content;
    xhr.setRequestHeader("X-CSRFToken", csrf_token);
    xhr.setRequestHeader("Content-Type", "application/json;charset=UTF-8");
    console.log(document.getElementById('display_area1').options[document.getElementById('display_area1').selectedIndex].label)
    xhr.send(JSON.stringify({'region': document.getElementById('display_area1').options[document.getElementById('display_area1').selectedIndex].label,
        'protector_height':document.getElementById('protector_height').value,
        'season':document.getElementById('sezonnost').options[document.getElementById('sezonnost').selectedIndex].label,
        'width':document.getElementById('shirina_profilya').options[document.getElementById('shirina_profilya').selectedIndex].label,
        'height':document.getElementById('vysota_profilya').options[document.getElementById('vysota_profilya').selectedIndex].label,
        'diametr':document.getElementById('diametr').options[document.getElementById('diametr').selectedIndex].label, 'pages':10}));
    });
}

//Функция обновления графика, вызываемая по расписанию
function updateChart(graphData){
//    console.log("We're here")
    Plotly.newPlot('chart',graphData,{});

}

//Событие нажатия кнопки Обновить
if (document.getElementById('GetAvitoTirePrices')) {
    document.getElementById('GetAvitoTirePrices').addEventListener('click', function () {
//    При смене региона надо перерисовать график
    var element = document.getElementById('GetAvitoTirePrices');
    var xhr = new XMLHttpRequest();
    xhr.open('post', 'updateTirePrices');
    xhr.onload = function() {
        if (this.readyState === 4 && this.status === 200) {
            var graphs = JSON.parse(xhr.response);
            Plotly.newPlot('chart',graphs,{});
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
        'season':document.getElementById('sezonnost').options[document.getElementById('sezonnost').selectedIndex].label,
        'width':document.getElementById('shirina_profilya').options[document.getElementById('shirina_profilya').selectedIndex].label,
        'height':document.getElementById('vysota_profilya').options[document.getElementById('vysota_profilya').selectedIndex].label,
        'diametr':document.getElementById('diametr').options[document.getElementById('diametr').selectedIndex].label, 'pages':10}));
    });
}

//Событие нажатия кнопки Обновить
if (document.getElementById('Refresh')) {
    document.getElementById('Refresh').addEventListener('click', function () {
//    При смене региона надо перерисовать график
    var element = document.getElementById('Refresh');
    var xhr = new XMLHttpRequest();
    xhr.open('post', 'updateChartNow');
    xhr.onload = function() {
        if (this.readyState === 4 && this.status === 200) {
//            console.log(graphs)
            var graphs = JSON.parse(JSON.parse(xhr.response)['chartData']);
            Plotly.newPlot('chart',graphs,{});
            document.getElementById('recommended_price').value = JSON.parse(JSON.parse(xhr.response)['predictResult']) * document.getElementById('qte').value
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
        'season':document.getElementById('sezonnost').options[document.getElementById('sezonnost').selectedIndex].label,
        'width':document.getElementById('shirina_profilya').options[document.getElementById('shirina_profilya').selectedIndex].label,
        'height':document.getElementById('vysota_profilya').options[document.getElementById('vysota_profilya').selectedIndex].label,
        'diametr':document.getElementById('diametr').options[document.getElementById('diametr').selectedIndex].label, 'pages':10}));
    });
}
