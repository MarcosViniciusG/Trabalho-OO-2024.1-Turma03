function mostrarSenha(tipo) {
    let el;
    if (tipo=="cadastro")
        el = document.getElementById("cadastro-senha");
    else if (tipo=="login")
        el = document.getElementById("login-senha");

    if (el.type === "password") {
        el.type = "text";
    } else {
        el.type = "password";
    }
}

function mostrarObras() {
    const el = document.getElementById("obras")
    if (el.style.display === "none")
        el.style.display = "grid";
    else
        el.style.display = "none";
}

function mostrarColecoes() {
    const el = document.getElementById("colecoes")
    if (el.style.display === "none")
        el.style.display = "grid";
    else
        el.style.display = "none";
}

function ativarObra(obras, id) {
    const obra = obras[id]
    central = document.getElementById("central");
    central.style.textAlign = "left";
    central.innerHTML = `
        <img class='central-img' src="${obra['caminho']}"/>
        <p>Título: ${obra['titulo']}</p>
        <p>Autor: ${obra['autor']}</p>
        <p>Ano: ${obra['ano']}</p>
        <p>Estilo: ${obra['estilo']}</p>
        <p>Descrição: ${obra['descricao']}</p>
        <p>Peça para o ChatGPT gerar um poema inspirado na obra de arte:
        <form action="${obra['chatgpt']}" method="POST">
            <input type="hidden" name="titulo" value=${obra['titulo']}>
            <input type="hidden" name="colecaoId" value=${obra['colecaoId']}>
            <input type="hidden" name="autor" value="${obra['autor']}">
            <button type="submit" class="botao">Pedir</button>
        </form>
    `;
    central.scrollIntoView();
}