const $form = $("form[name='form']");

$form.before(`<p style="font-weight:bold; color:green; text-align:center;">Auto-filled by userscript!<br>Also hi, r/neopets discord :)</p>`).find("select").each(function (index, element) {
    const numOptions = $(element).find("option").length;
    const random = Math.floor(Math.random() * (numOptions - 1)) + 1;
    $(element).find("option").eq(random).prop("selected", true);
});

if (document.URL.includes("grumpyking")) {
    //["What", "do", "you do if", "*Leave blank*", "fierce", "Peophins", "*Leave blank*", "has eaten too much", "*Leave blank*", "tin of olives"];
    const avOptions = [3, 8, 6, 1, 39, 118, 1, 32, 1, 143];
    for (let i = 0; i < 10; i++) {
        $(`#qp${i + 1} option`).eq(avOptions[i]).prop("selected", true);
    }
}
