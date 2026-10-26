// Mensajes del frontend MVC; los contratos y validadores REST se conservan.
(function () {
    document.querySelectorAll("[data-val=true]").forEach(function (field) {
        var label = document.querySelector('label[for="' + field.id + '"]');
        var name = label ? label.textContent.trim() : "valor";
        var messages = {
            required: "El campo «" + name + "» es obligatorio.",
            number: "Introduce un número válido.",
            date: "Introduce una fecha válida.",
            regex: "Selecciona un valor válido.",
            length: "El campo admite como máximo " + field.getAttribute("data-val-length-max") + " caracteres.",
            range: "Introduce un valor entre " + field.getAttribute("data-val-range-min") + " y " + field.getAttribute("data-val-range-max") + "."
        };
        Object.keys(messages).forEach(function (rule) {
            if (field.hasAttribute("data-val-" + rule)) field.setAttribute("data-val-" + rule, messages[rule]);
        });
    });
    if (window.jQuery && jQuery.validator) {
        jQuery.extend(jQuery.validator.messages, {
            required: "Este campo es obligatorio.",
            number: "Introduce un número válido.",
            date: "Introduce una fecha válida.",
            min: jQuery.validator.format("Introduce un valor mayor o igual a {0}."),
            max: jQuery.validator.format("Introduce un valor menor o igual a {0}."),
            maxlength: jQuery.validator.format("Introduce como máximo {0} caracteres."),
            range: jQuery.validator.format("Introduce un valor entre {0} y {1}.")
        });
    }
})();
