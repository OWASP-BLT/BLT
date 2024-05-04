"use strict";

(function (_jQuery) {
  const $ = _jQuery, jQuery = _jQuery;
  if (window.dbdpInitialized) return;
  window.dbdpInitialized = true;
  /**
   * @typedef {object} WidgetInstance
   * @property {WidgetInputConfig} config
   * @property {jQueryElement} $element
   * @property {DateTimePickerData} dateTimePickerData
   *
   * @typedef {object} DateTimePickerData
   * @property {Function} date
   *
   * @typedef {object} WidgetOptions
   * @property {object} icons
   *
   * @typedef {object} WidgetInputConfig
   * @property {string} variant
   * @property {string} backend_date_format
   * @property {WidgetOptions} options
   * @property {string} range_from
   */

  const inputWrapperClass = "dbdp";
  /** @type {WeakMap<HTMLInputElement, WidgetInstance>} */
  const widgetInstances = new WeakMap();
  /** @type {WidgetOptions} */
  const defaultWidgetOptions = {
    icons: {
      time: 'bi-clock',
      date: 'bi-calendar',
      up: 'bi-chevron-up',
      down: 'bi-chevron-down',
      previous: 'bi-chevron-left',
      next: 'bi-chevron-right',
      today: 'bi-record-circle',
      clear: 'bi-trash',
      close: 'bi-x-lg'
    }
  }

  document.addEventListener('DOMContentLoaded', function (event) {
    setTimeout(() => findAndProcessInputs(document));
    document.addEventListener('DOMNodeInserted', function (event) {
      setTimeout(() => {
        if (event.target.querySelectorAll) findAndProcessInputs(event.target);
      });
    });
  });

  /**
   * @param {HTMLElement} htmlElement
   */
  function findAndProcessInputs(htmlElement) {
    /** @type {NodeListOf<HTMLInputElement>} */
    const inputElements = htmlElement.querySelectorAll('[data-dbdp-config]:not([disabled])')
    for (const inputElement of inputElements) {
      try {
        if (!jQuery) throw new DisplayError("You have to load jQuery before form.media");
        if (!("moment" in window)) throw new DisplayError("momentjs was not loaded, is your momentjs_url valid?");
        if (!("datetimepicker" in jQuery.fn)) throw new DisplayError("datetimepicker js was not loaded, is your datetimepicker_js_url valid?");
        processInputElement(inputElement);
      } catch (err) {
        handleErrorAndThrow(err, inputElement);
      }
    }
    findAndProcessDeprecatedRangeInputs(htmlElement);
  }

  /**
   * @param {HTMLInputElement} inputElement
   */
  function processInputElement(inputElement) {
    const config = getConfig(inputElement);
    const inputWrapper = inputElement.closest(`.${inputWrapperClass}`);
    if (!inputWrapper) throw Error(`input must have a parent with class="${inputWrapperClass}"`)
    const hiddenInputElement = createHiddenInputElement(inputElement)
    inputWrapper.after(hiddenInputElement)

    if (!config.options.format) config.options.format = config.backend_date_format.replace(/-01/g, "")
    if (config.range_from) config.options.useCurrent = false; // based on https://github.com/Eonasdan/tempus-dominus/issues/1075
    const widgetInstance = createWidgetInstance(inputWrapper, hiddenInputElement, config);
    widgetInstances.set(hiddenInputElement, widgetInstance);

    if (config.range_from) {
      const widgetRangeFromInstance = getRangeFromInputElement(hiddenInputElement, config);
      if (widgetRangeFromInstance) {
        configureRangeSelection(widgetRangeFromInstance, widgetInstance);
      }
    }
  }

  /**
   * @param {HTMLInputElement} inputElement
   */
  function createHiddenInputElement(inputElement) {
    const formInputElement = document.createElement("input")
    formInputElement.setAttribute("type", "hidden")
    formInputElement.setAttribute("name", inputElement.getAttribute("name"))
    inputElement.dataset.name = inputElement.getAttribute("name")
    formInputElement.value = inputElement.value
    inputElement.removeAttribute("name")
    return formInputElement;
  }

  /**
   * @param {HTMLElement} inputWrapper
   * @param {HTMLInputElement} hiddenInputElement
   * @param {WidgetInputConfig} config
   */
  function createWidgetInstance(inputWrapper, hiddenInputElement, config) {
    const $inputWrapper = jQuery(inputWrapper).datetimepicker(config.options);
    /** @type {WidgetInstance} */
    const widgetInstance = { config, $element: $inputWrapper, dateTimePickerData: $inputWrapper.data("DateTimePicker") }
    widgetInstance.dateTimePickerData.date(moment(hiddenInputElement.value, config.backend_date_format));
    widgetInstance.$element.on("dp.change", function (e) {
      hiddenInputElement.value = e.date ? e.date.format(config.backend_date_format) : null;
    });
    for (let [eventName, handler] of Object.entries(config.events)) {
      widgetInstance.$element.on(eventName, handler);
    }
    return widgetInstance;
  }

  /**
   * @param {HTMLInputElement} inputElement
   */
  function getConfig(inputElement) {
    let /** @type {WidgetInputConfig} */ config;
    try {
      config = JSON.parse(inputElement.dataset.dbdpConfig);
    }
    catch (err) { throw Error("Invalid input config") }
    const optionKeyName = inputElement.name.replace(/^(.*-)?/, "dbdpOptions_")
    config.options = { ...defaultWidgetOptions, ...window.dbdpOptions, ...window[optionKeyName], ...config.options };
    config.events = { ...window.dbdpEvents, ...window[optionKeyName.replace("dbdpOptions_", "dbdpEvents_")] };
    return config;
  }

  /**
   * @param {HTMLInputElement} hiddenInputElement
   * @param {WidgetInputConfig} config
   */
  function getRangeFromInputElement(hiddenInputElement, config) {
    const rangeFromInputName = hiddenInputElement.name.replace(/[^-]+$/, config.range_from);
    let fromInputElement = hiddenInputElement.form?.elements.namedItem(rangeFromInputName);
    if (!fromInputElement) {
      const elements = document.querySelectorAll(`input[name="${config.range_from}"]`);
      if (elements.length == 0) throw Error("range_from not found");
      if (elements.length > 1) throw Error("Multiple range_from found");
      fromInputElement = elements[0];
    }
    if (widgetInstances.has(fromInputElement)) {
      return widgetInstances.get(fromInputElement);
    } else {
      throw Error(`range_from "${config.range_from}" is not a widget input`);
    }
  }

  /**
   * @param {WidgetInstance} fromInstance
   * @param {WidgetInstance} toInstance
   */
  function configureRangeSelection(fromInstance, toInstance) {
    fromInstance.dateTimePickerData.maxDate(toInstance.dateTimePickerData.date() || false);
    toInstance.dateTimePickerData.minDate(fromInstance.dateTimePickerData.date() || false);
    fromInstance.$element.on("dp.change", function (e) {
      toInstance.dateTimePickerData.minDate(e.date || false);
    });
    toInstance.$element.on("dp.change", function (e) {
      fromInstance.dateTimePickerData.maxDate(e.date || false);
    });
  }

  class DisplayError extends Error { }
  class WidgetError extends Error {
    /**
     * @param {HTMLInputElement} inputElement
     * @param {string} message
     * @param {boolean} shouldDisplay
     */
    constructor(inputElement, message) {
      super(`input name: ${inputElement.name || inputElement.dataset.name}; ${message}`);
      this.name = "django-bootstrap-datepicker-plus error";
    }
  }

  /**
   * @param {Error} error
   * @param {HTMLInputElement?} inputElement
   */
  function handleErrorAndThrow(error, inputElement) {
    if (inputElement?.hasAttribute('data-dbdp-debug')) {
      const errorMessage = error instanceof DisplayError ? error.message : "Something went wrong! Check browser console for errors.";
      const errorDisplay = document.createElement("div");
      errorDisplay.className = "alert alert-danger"
      errorDisplay.innerHTML = `${errorMessage}. This message is only visible when DEBUG=True`;
      inputElement.closest(`.${inputWrapperClass}`).after(errorDisplay);
    }
    throw new WidgetError(error.message);
  }

  /**
   * @param {HTMLElement} htmlElement
   */
  function findAndProcessDeprecatedRangeInputs(htmlElement) {
    const fromInputs = htmlElement.querySelectorAll('[data-dbdp-start]:not([disabled])')
    for (const fromInput of fromInputs) {
      const eventName = fromInput.dataset.dbdpStart;
      const toInput = htmlElement.querySelector(`input[data-dbdp-end="${eventName}"]:not([disabled])`);
      if (!toInput) continue;
      const fromHiddenInput = fromInput.closest(`.${inputWrapperClass}`)?.nextElementSibling;
      const toHiddenInput = toInput.closest(`.${inputWrapperClass}`)?.nextElementSibling;
      if (fromHiddenInput && toHiddenInput && widgetInstances.has(fromHiddenInput) && widgetInstances.has(toHiddenInput)) {
        configureRangeSelection(widgetInstances.get(fromHiddenInput), widgetInstances.get(toHiddenInput));
      }
    }
  }

  if ("bootstrap" in window) { // if bootstrap version >= 4
    $('body').on("dp.show", `.${inputWrapperClass}`, function (e) {
      $(e.target).find('.collapse.in').addClass('show');
    });
    $('body').on('show.bs.collapse', '.bootstrap-datetimepicker-widget .collapse', function (e) {
      $(e.target).addClass('in');
    });
    $('body').on('hidden.bs.collapse', '.bootstrap-datetimepicker-widget .collapse', function (e) {
      $(e.target).removeClass('in');
    });
  }
})(window.jQuery);
