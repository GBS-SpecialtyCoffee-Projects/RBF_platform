/*!
 * evk_calendar_jk.js 1.0.0
 * https://github.com/JohnKu2020/evk_calendar
 *
 * Released under the MIT
 * https://github.com/JohnKu2020/evk_calendar/blob/main/LICENSE
 */
(function($) {
	$.fn.evkJKcalendar = function (options) {
		'use strict';
		return $(this).each(function () {
			var defaults = { lang: 'en', width: '100%', backgroundcolor: 'transparent', color: '#000000', canPast: false, initDate: null},
			activeOptions = $.extend(defaults, options),
			self = this,
			element = $(this),
			element_id = element.attr("id"),
			element_class = 'evk_calendar',
			CurrentDay = new Date().getDate(),
			CurrentMonth = new Date().getMonth(),
			CurrentYear = new Date().getFullYear(),
			Today = new Date().getDate(),
			DaysHeader='',
			LastRow='',
			tr_count = 0,
			lang = '',
			calendar = '',
			canPast = false,
			empty_day = '<td class="сEmpty">&nbsp;</td>',
			initElement = function (show_month = CurrentMonth, show_year = CurrentYear) {
				//if ( activeOptions.initDate!=null) {var inDate = new Date(activeOptions.initDate); show_month = inDate.getMonth(); show_year = inDate.getFullYear(); CurrentMonth = inDate.getMonth(); CurrentYear = inDate.getFullYear();}
				if (activeOptions['lang'] === undefined || activeOptions['lang'] === null) { var strings = new Object(); if(navigator.browserLanguage){ lang = navigator.browserLanguage; } else { lang = navigator.language; }; lang = lang.substr(0,2).toLowerCase(); if (lang === undefined || lang === null) lang = 'ru'; } else { lang = activeOptions['lang']; }
				if(lang=='en'){ 
					var nmonth=["January","February","March","April","May","June","July","August","September","October","November","December"], nday=["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]; 
				} else if(lang=='ua') { 
					var nmonth=["Січень","Лютий","Березень","Квітень","Травень","Червень","Липень","Серпень","Вересень","Жовтень","Листопад","Грудень"], nday=["Пн","Вт","Ср","Чт","Пт","Сб","Нд"]; 
				} else {
					var nmonth=["Январь","Февраль","Март","Апрель","Май","Июнь","Июль","Август","Сентябрь","Октябрь","Ноябрь","Декабрь"], nday=["Пн","Вт","Ср","Чт","Пт","Сб","Вс"]; 
				}
				var Dlast = new Date(show_year,show_month+1,0).getDate(), D = new Date(show_year,show_month,Dlast), DNlast = new Date(D.getFullYear(),D.getMonth(),Dlast).getDay(), DNfirst = new Date(D.getFullYear(),D.getMonth(),1).getDay(), curr_cls='';
				calendar = '<tr>'; tr_count = 0; LastRow = '';
				if (DNfirst != 0) { for(var i = 1; i < DNfirst; i++) calendar += empty_day; } else { for(var i = 0; i < 6; i++) calendar += empty_day; }
				for (var i = 1; i <= Dlast; i++) {
					var curFormatted = format_event_date(CurrentYear, CurrentMonth, i);
					if (i == new Date().getDate() && D.getFullYear() == new Date().getFullYear() && D.getMonth() == new Date().getMonth()) { curr_cls = 'сToday'; } else { curr_cls = 'cDay';}
					if ( activeOptions.initDate!=null && isDatebyDefault(curFormatted, activeOptions.initDate)) curr_cls += ' selected ';
					if (isDateInPastExcludingToday(format_event_date(CurrentYear, CurrentMonth, i))) curr_cls = 'cNone';
					calendar += '<td class="'+curr_cls+'" data-id="'+  curFormatted + '">' + i +'</td>';
					if (new Date(D.getFullYear(),D.getMonth(),i).getDay() == 0) { calendar += '<tr>'; tr_count++; }
				}
				for (var i = DNlast; i < 7; i++) calendar += empty_day;
				DaysHeader = ''; for(var i = 0; i < 7; i++) DaysHeader += '<td>'+nday[i]+'</td>';
				LastRow = ''; if (tr_count < 5) LastRow = '<tr><td colspan="7" class="сEmpty">&nbsp;</td></tr>';
				element.html('<table class="'+element_class+'" style="background-color:'+activeOptions.backgroundcolor+';color:'+activeOptions.color+';width:'+activeOptions.width+'">'
								+'<thead><tr><td class="y_Prev"></td><td colspan="5" data-month="'+D.getMonth()+1+'" data-year="'+D.getFullYear()+'">'+ D.getFullYear()+'</td><td class="y_Next"></td></tr>'
								+'<tr><td class="m_Prev"></td><td style="font-size: 18px; padding: 0 0 10px; font-weight: 500;" colspan="5" data-month="'+D.getMonth()+1+'" data-year="'+D.getFullYear()+'">'+nmonth[D.getMonth()] +'</td><td class="m_Next"></td></tr></thead>'
								+'<tbody><tr>'+DaysHeader+'</tr>'+calendar+LastRow+'</tbody></table>')
						.css('cursor', 'pointer');
			},
			format_event_date = function (iyear, imonth, iday) {
				var Dlast = new Date(CurrentYear,CurrentMonth+1,0).getDate(), D = new Date(CurrentYear,CurrentMonth,Dlast), d_month = D.getMonth()+1;
				return D.getFullYear()+'-'+d_month.toString().padStart(2, "0")+'-'+iday.toString().padStart(2, "0");
			},
			isDateInPastExcludingToday = function (checkDate) { //2023-01-01
				var currentDate = new Date(); 
				currentDate.setHours(0, 0, 0, 0);
				checkDate = new Date(checkDate);
				checkDate.setHours(23, 59, 59, 999);
				return checkDate < currentDate;				
			},
			isDatebyDefault = function (D1, D2) { //2023-01-01
				if ( D2 === undefined || D2 === null || D2 == '') return false;
				var Date1 = new Date(D1);
				var D1_str = Date1.getFullYear() + '-' + Date1.getMonth() + '-' + Date1.getDate();
				var Date2 = new Date(D2);
				var D2_str = Date2.getFullYear() + '-' + Date2.getMonth() + '-' + Date2.getDate();
				return ( D1_str == D2_str);
			}
			initElement();
			element.on('click', '.m_Prev', function (e) {
				if (e.which!=1) return false; e.preventDefault();
				CurrentMonth--; if (CurrentMonth<0) { CurrentMonth=11; CurrentYear--; }
				initElement(CurrentMonth, CurrentYear);
				var evt = $.Event('month_prev'); element.trigger(evt, format_event_date(CurrentYear, CurrentMonth+1, 1));
			});
			element.on('click', '.m_Next', function (e) {
				if (e.which!=1) return false; e.preventDefault();
				CurrentMonth++; if (CurrentMonth>12) { CurrentMonth=1; CurrentYear++; }
				initElement(CurrentMonth, CurrentYear);
				var evt = $.Event('month_next'); element.trigger(evt, format_event_date(CurrentYear, CurrentMonth+1, 1));
			});
			element.on('click', '.y_Prev', function (e) {
				if (e.which!=1) return false; e.preventDefault(); CurrentYear--; initElement(CurrentMonth, CurrentYear);
				var evt = $.Event('year_prev'); element.trigger(evt, format_event_date(CurrentYear, CurrentMonth+1, 1));
			});
			element.on('click', '.y_Next', function (e) {
				if (e.which!=1) return false; e.preventDefault(); CurrentYear++; initElement(CurrentMonth, CurrentYear);
				var evt = $.Event('year_next'); element.trigger(evt, format_event_date(CurrentYear, CurrentMonth+1, 1));
			});
			element.on('click', '.cDay, .сToday', function (e) {
				e.preventDefault();
				if (e.which!=1) return false;
				var ClickDay=$(e.target).attr('data-id');
				element.find('td.cDay, td.сToday').removeClass('selected');$(this).addClass('selected');
				if (ClickDay!=CurrentDay) {
					CurrentDay=ClickDay;
					var evt = $.Event('change'); element.trigger(evt, ClickDay);
				}
			});
		});
	}
})(jQuery);
