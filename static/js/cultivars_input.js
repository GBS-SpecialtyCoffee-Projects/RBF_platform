// Progressive-enhancement widget for the cultivars field.
//
// The real Django `cultivars` input (comma-separated) is hidden and kept in
// sync; the user edits individual cultivars in separate inputs and can add or
// remove rows. Storage stays comma-separated, so nothing changes server-side.
//
// Markup contract:
//   <div class="cultivars-widget">
//     <div class="cultivars-original"> {{ form.cultivars }} </div>
//   </div>
(function () {
  "use strict";

  function initWidget(wrapper) {
    var original = wrapper.querySelector(".cultivars-original");
    var field = wrapper.querySelector("input[name], textarea[name]");
    if (!field) return;
    if (original) original.style.display = "none";

    var list = document.createElement("div");
    list.className = "cultivars-list";

    var addBtn = document.createElement("button");
    addBtn.type = "button";
    addBtn.className = "btn btn-sm btn-outline-secondary";
    addBtn.textContent = "+ Add cultivar";

    function sync() {
      var values = [];
      list.querySelectorAll("input.cultivar-item").forEach(function (inp) {
        var v = inp.value.trim();
        if (v) values.push(v);
      });
      field.value = values.join(",");
    }

    function addRow(value) {
      var row = document.createElement("div");
      row.className = "input-group mb-2 cultivar-row";

      var input = document.createElement("input");
      input.type = "text";
      input.className = "form-control cultivar-item";
      input.placeholder = "Cultivar";
      input.value = value || "";
      input.addEventListener("input", sync);

      var remove = document.createElement("button");
      remove.type = "button";
      remove.className = "btn btn-outline-danger";
      remove.setAttribute("aria-label", "Remove cultivar");
      remove.textContent = "×"; // ×

      remove.addEventListener("click", function () {
        row.remove();
        if (!list.querySelector(".cultivar-row")) addRow("");
        sync();
      });

      row.appendChild(input);
      row.appendChild(remove);
      list.appendChild(row);
      return input;
    }

    addBtn.addEventListener("click", function () {
      addRow("").focus();
      sync();
    });

    var existing = (field.value || "")
      .split(",")
      .map(function (s) { return s.trim(); })
      .filter(function (s) { return s; });
    if (existing.length === 0) existing = [""];
    existing.forEach(addRow);

    wrapper.appendChild(list);
    wrapper.appendChild(addBtn);

    // Defensive: make sure the hidden field is current on submit.
    var form = wrapper.closest("form");
    if (form) form.addEventListener("submit", sync);

    sync();
  }

  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".cultivars-widget").forEach(initWidget);
  });
})();
