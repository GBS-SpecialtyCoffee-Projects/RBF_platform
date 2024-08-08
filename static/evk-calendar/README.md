# evk_calendar
Simple jQuery based calendar script - another one :smile:

Plain, clear and easy to use!

Sometimes you need **SIMPLE** calendar just to browse dates and send aJAX requests.

I've found nothing! That's why all this about :boom:

Output format is **YYYY-MM-DD** to fit MySQL requests

Calendar has a super-puper feature :100:  - auto language detection!

If you need a bit more features feel free to write comments :left_speech_bubble: ! 

## Setup
```
<script type="text/javascript" src="evk_calendar_jk.js"></script>
<link href="evk_calendar_jk.css" rel="stylesheet" type="text/css">
```
## Usage
```
<script type="text/javascript">
$(document).ready(function(){

	$('#cale').evkJKcalendar(); // Force language select: $('#cale').evkJKcalendar({lang:'en'});

	// Events
	$("#cale").on('change',function(e, date){
		log('date: '+date);
	}).on('month_prev',function(e, month){
		log('month: '+month);
	}).on('month_next',function(e, month){
		log('month: '+month);
	}).on('year_prev',function(e, year){
		log('year: '+year);
	}).on('year_next',function(e, year){
		log('year: '+year);
	});
  
});
</script>
<div class="row"><div class="col-lg-3"><div id="cale"></div></div></div>
```
## Options
```
{ lang: 'ru|en', width: '100%', backgroundcolor: 'transparent', color: '#000000'}
```
## How it looks like
![How it looks](https://evk.ru.com/demo/github/evk_calendar_jk_js/evk_calendar_jk_js.jpg)

## Demo
You can see a [demo and usage here](https://evk.ru.com/demo/github/evk_calendar_jk_js)

## License

(The MIT License)

Copyright (c) 2023 John Ku

Permission is hereby granted, free of charge, to any person obtaining
a copy of this software and associated documentation files (the
'Software'), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to
the following conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED 'AS IS', WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
