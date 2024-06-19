            # IMPORTS E CONFIGURAÇÃO DO FLASK
from flask import Flask, render_template, request, redirect, url_for, session, flash, Markup
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError
from openai import OpenAI
from abc import ABC, abstractmethod

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///minhabase.sqlite3'
app.secret_key = '123456'
db = SQLAlchemy(app)
app.app_context().push()

            # CONFIGURAÇÃO DO CHATGPT
client = OpenAI(api_key = '')

def perguntar(prompt):
    response = client.chat.completions.create(
    model="gpt-3.5-turbo-0125",
    response_format={ "type": "text" },
    messages=[
         {"role": "system", "content": "Crie um poema inspirado na obra de arte dada pelo usuário, ele enviará o título da obra e seu autor. RETORNE SOMENTE O POEMA SEM MAIS NENHUM TEXTO ADICIONAL."},
         {"role": "user", "content": prompt}
          ]
    )
    return response.choices[0].message.content

            # CLASSES PARA UTILIZAR O BANCO DE DADOS
class Usuario(db.Model):
    __tablename__ = "usuarios"
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String, unique=True)
    senha = db.Column(db.String)

    def __init__(self, nome, senha):
        self.nome = nome
        self.senha = senha

class ObraDB(db.Model):
    __tablename__ = "obras"
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(100), nullable=False)
    autor = db.Column(db.String(100), nullable=False)
    estilo = db.Column(db.String(50))
    ano = db.Column(db.Integer)
    caminho = db.Column(db.String(200), nullable=False)
    descricao = db.Column(db.Text)

class ColecaoDB(db.Model):
    __tablename__ = "colecoes"
    id = db.Column(db.Integer, primary_key=True)
    usuarioId = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    nome = db.Column(db.String(100), nullable=False)
    descricao = db.Column(db.Text)

    def __init__(self, nome, descricao, usuarioId):
        self.nome = nome
        self.descricao = descricao
        self.usuarioId = usuarioId

class ColecaoItem(db.Model):
    __tablename__ = "colecoesItens"
    id = db.Column(db.Integer, primary_key=True)
    colecaoId = db.Column(db.Integer, db.ForeignKey('colecoes.id'), nullable=False)
    tipo = db.Column(db.String(10), nullable=False)  # colecao ou obra
    itemId = db.Column(db.Integer, nullable=False)

    def __init__(self, colecaoId, tipo, itemId):
        self.colecaoId = colecaoId
        self.tipo = tipo
        self.itemId = itemId

            # CLASSES IMPLEMENTANDO OS PADRÕES DE PROJETO

class Obra():
    def __init__(self, item, id):
        self.tipo = "obra"
        self.__item = item
        self.__id = id

    def getTipo(self):
        return self.tipo

    def getDetalhes(self):
        return {
            "tipo": "obra",
            "itemId": self.__item.id,
            "titulo": self.__item.titulo,
            "autor": self.__item.autor,
            "estilo": self.__item.estilo,
            "ano": self.__item.ano,
            "caminho": self.__item.caminho,
            "descricao": self.__item.descricao,
            "id": self.__id
        }

class Colecao(Obra):
    def __init__(self, nome, descricao, id, itemId):
        self.__nome = nome
        self.__descricao = descricao
        self.__id = id
        self.tipo = "colecao"
        self.__itens = []
        self.__itemId = itemId

    def addItem(self, item):
        self.__itens.append(item)

    def getColecao(self):
        return self.__itens

    def getDetalhes(self):
        return {
            "tipo": "colecao",
            "itemId": self.__itemId,
            "id": self.__id,
            "nome": self.__nome,
            "descricao": self.__descricao,
        }


    def getObras(self):
        obras = []
        iterator = FabricaIterator.criar(self, "obras")
        for obra in iterator:
            obras.append(obra)
        return obras

    def getNivelInicial(self):
        nivelInicial = []
        iterator = FabricaIterator.criar(self, "nivelInicial")
        for item in iterator:
            nivelInicial.append(item)
        return nivelInicial

class Iterator(ABC):
    @abstractmethod
    def __iter__(self):
        pass

    @abstractmethod
    def __next__(self):
        pass

class IteratorObras(Iterator):
    def __init__(self, colecao):
        self.pilha = []
        self.pilha.append(colecao)

    def __iter__(self):
        return self

    def __next__(self):
        while self.pilha:
            atual = self.pilha.pop()
            if(atual.getTipo() == "colecao"):
                for el in reversed(atual.getColecao()):
                    self.pilha.append(el)
            else:
                return atual.getDetalhes()
        raise StopIteration

class IteratorNivelInicial(Iterator):
    def __init__(self, colecao):
        self.lista = []
        self.lista = colecao

    def __iter__(self):
        return self

    def __next__(self):
        if self.lista:
            x = self.lista.pop()
            return x.getDetalhes()

        raise StopIteration

class FabricaIterator:
    @staticmethod
    def criar(colecao, tipo):
        if(tipo == "obras"):
            return IteratorObras(colecao)
        if(tipo == "nivelInicial"):
            return IteratorNivelInicial(colecao.getColecao())

        raise ValueError("Não foi possível criar o Iterator solicitado, verifique se você informou um tipo válido")

def carregarColecao(colecaoId):
    q = ColecaoItem.query.filter_by(itemId=colecaoId).first()
    if q is not None:
        id = q.id
    else:
        id = None
    colecao = ColecaoDB.query.filter_by(id=colecaoId).first()
    colecaoObj = Colecao(colecao.nome, colecao.descricao, id, colecaoId)
    colecaoItens = ColecaoItem.query.filter_by(colecaoId=colecaoId).all()

    for item in colecaoItens:
        if item.tipo == 'obra':
            obra = ObraDB.query.get(item.itemId)
            obraObj = Obra(obra, item.id)
            colecaoObj.addItem(obraObj)
        elif item.tipo == 'colecao':
            subColecaoObj = carregarColecao(item.itemId)
            colecaoObj.addItem(subColecaoObj)

    return colecaoObj

def encontrarColecoesPais(colId, exclude=None):
    if exclude is None:
        exclude = []

    paisLinhas = ColecaoItem.query.filter_by(itemId=colId, tipo='colecao').all()
    paisDiretos = [linha.colecaoId for linha in paisLinhas]

    for pai in paisDiretos:
        if pai not in exclude:
            exclude.append(pai)
            encontrarColecoesPais(pai, exclude)

    return exclude



def verificarLogin(nome, senha):
    return (Usuario.query.filter_by(nome=nome, senha=senha).first() is not None)

errorTemplate = '''
        <head>
            <link rel="stylesheet" type="text/css" href={}>
        </head>
        <li class="error">Você não está logado. Retorne para a página inicial e realize o <a href={}>login</a>.</li>
        '''

@app.route("/", methods=['POST', 'GET'])
def index():
    return render_template('index.html')

@app.route("/cadastrar", methods=['POST'])
def adicionarUsuario():
    nome = request.form['nome']
    senha = request.form['senha']
    user = Usuario(nome, senha)
    try:
        db.session.add(user)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash("Nome de usuário já existe. Por favor, escolha outro nome.", "error")

    return redirect(url_for("index"))

@app.route("/home", methods=['POST', 'GET'])
def home():
    if 'nome' in session:
        usuarioId = Usuario.query.filter_by(nome=session['nome']).first().id
        colecoes = ColecaoDB.query.filter_by(usuarioId=usuarioId).all()
        return render_template('home.html', colecoes=colecoes)

    errorMsg = errorTemplate.format(url_for('static', filename='styles.css'), url_for("index"))
    return Markup(errorMsg)

@app.route("/login", methods=['POST'])
def login():
    nome = request.form['nome']
    senha = request.form['senha']
    if verificarLogin(nome, senha):
        session['nome'] = nome
        return redirect(url_for("home"))

    flash("Nome ou senha incorreto. Por favor, tente novamente ou cadastre-se.", "error")
    return redirect(url_for("index"))

@app.route('/logout', methods=['GET'])
def logout():
    session.pop('nome', None)
    return redirect(url_for('index'))

@app.route("/adicionarColecao", methods=['POST'])
def adicionarColecao():
    nome = request.form['nome']
    descricao = request.form['descricao']

    if 'nome' in session:
        usuarioId = Usuario.query.filter_by(nome=session['nome']).first().id
        colecao = ColecaoDB(nome, descricao, usuarioId)
        try:
            db.session.add(colecao)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("Digite algum nome para a coleção.", "error")

    return redirect(url_for("home"))

@app.route("/excluirColecao", methods=['POST'])
def excluirColecao():
    colecaoId = request.form['colecaoId']

    if 'nome' in session:
        ColecaoItem.query.filter_by(colecaoId=colecaoId).delete()
        ColecaoItem.query.filter_by(itemId=colecaoId, tipo="colecao").delete()
        ColecaoDB.query.filter_by(id=colecaoId).delete()
        db.session.commit()

    return redirect(url_for("home"))

@app.route("/modificarColecao", methods=['POST'])
def modificarColecao():
    colecaoId = request.form['colecaoId']
    novoNome = request.form['novoNome']
    novaDescricao = request.form['novaDescricao']

    if 'nome' in session:
        try:
            ColecaoDB.query.filter_by(id=colecaoId).update({"nome": novoNome, "descricao": novaDescricao})
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("Digite algum nome para a coleção.", "error")

    return redirect(url_for("home"))

@app.route("/adicionarItemColecao", methods=['POST'])
def adicionarItemColecao():
    colecaoId = request.form['colecaoId']
    tipo = request.form['tipo']
    itemId = request.form['itemId']

    if 'nome' in session:
        if(tipo=="obra" or (tipo=="colecao" and colecaoId not in encontrarColecoesPais(itemId))):
            usuarioId = Usuario.query.filter_by(nome=session['nome']).first().id
            if(ColecaoDB.query.filter_by(id=colecaoId, usuarioId=usuarioId).first() is not None):
                colecaoItem = ColecaoItem(colecaoId, tipo, itemId)
                db.session.add(colecaoItem)
                db.session.commit()
            else:
                flash("Você não é o dono desta coleção.", "error")

    return redirect(url_for('visualizarColecao', colecaoId = colecaoId, tipoIterator="nivelInicial"))

@app.route("/excluirItemColecao", methods=['POST'])
def excluirItemColecao():
    colecaoId = request.form['colecaoId']
    id = request.form['id']

    if 'nome' in session:
        usuarioId = Usuario.query.filter_by(nome=session['nome']).first().id
        if(ColecaoDB.query.filter_by(id=colecaoId, usuarioId=usuarioId).first() is not None):
            ColecaoItem.query.filter_by(id=id).delete()
            db.session.commit()
        else:
            flash("Você não é o dono desta coleção.", "error")

    return redirect(url_for('visualizarColecao', colecaoId = colecaoId, tipoIterator="nivelInicial"))

@app.route('/colecao/<int:colecaoId>/<string:tipoIterator>', methods=['GET'])
def visualizarColecao(colecaoId, tipoIterator):
    if 'nome' in session:
        colecaoObj = carregarColecao(colecaoId)
        if tipoIterator=="obras":
            mostrar = colecaoObj.getObras()
        elif tipoIterator=="nivelInicial":
            mostrar = colecaoObj.getNivelInicial()

        obras = ObraDB.query.all()
        colecoes = ColecaoDB.query.all()
        exclude = encontrarColecoesPais(colecaoId)
        info = {
            "mostrar": mostrar,
            "colecaoId": colecaoId,
            "colecaoItens": colecaoObj,
            "obras": obras,
            "colecoes": colecoes,
            "exclude": exclude
            }
        return render_template("navegar.html", info=info)
    else:
        errorMsg = errorTemplate.format(url_for('static', filename='styles.css'), url_for("index"))
        return Markup(errorMsg)

@app.route("/chatgpt", methods=['POST'])
def chatgpt():
    if request.method == 'POST':
        titulo = request.form['titulo']
        autor = request.form['autor']
        colecaoId = request.form['colecaoId']
        prompt = "Título: {} Autor: {}".format(titulo, autor)
        resposta = perguntar(prompt)

        flash(f"Poema: {resposta}", "nada")
        return redirect(url_for('visualizarColecao', colecaoId = colecaoId, tipoIterator="nivelInicial"))

with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run()