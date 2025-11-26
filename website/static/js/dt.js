
var MtrDatepickerDemo = (function() {

	var datepickers = [];
	var exportSettings;

	var init = function(config, settings) {
		exportSettings = settings;
		var datepicker = new MtrDatepicker(config);
		datepickers.push(datepicker);

		var exportFormatsContainer = document.getElementById(settings.exportFormats);
	 	datepickerChange(exportFormatsContainer, datepicker,settings.exportFormats);

	 	datepicker.onChange('all', function() {
			datepickerChange(exportFormatsContainer, datepicker, settings.exportFormats);
		});

		return datepicker;
	};

	function datepickerChange(resultElement, datepicker, elemId) {
		var result = datepicker.format('YYYY-MM-DD HH:mm');
		if(elemId=="datepicker-1-res"){
			$("#id_start_date").val(result);
		}
		else if(elemId=="datepicker-2-res"){
			$("#id_end_date").val(result);
		}
		resultElement.innerHTML = result;
	}

	return {
		init: init
	};

})();
