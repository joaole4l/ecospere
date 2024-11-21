from flask import Flask, render_template, request, redirect, url_for, flash, session, g, jsonify
import os
import sqlite3
from datetime import datetime
import base64

app = Flask(__name__)
app.secret_key = 'sua_chave_secreta'  # Mantenha esta chave em segredo

# Configuração do diretório de upload
UPLOAD_FOLDER = 'static/uploads/'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Função para conectar ao banco de dados
def get_db_connection():
    conn = sqlite3.connect('C:/Users/jv175/Documents/REDE SOCIAL (4) (1)/REDE SOCIAL/banco_de_dados.db')
    conn.row_factory = sqlite3.Row
    return conn

# Função para verificar se a extensão do arquivo é permitida
def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Inicialização do banco de dados
def init_db():
    banco = get_db_connection()
    cursor = banco.cursor()

    # Excluir a tabela posts se já existir
    cursor.execute('DROP TABLE IF EXISTS posts')

    cursor.execute(''' 
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            sobrenome TEXT NOT NULL,
            telefone TEXT NOT NULL,
            cpf TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            senha TEXT NOT NULL,
            profile_image TEXT
        )
    ''')

    cursor.execute(''' 
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            content TEXT NOT NULL,
            image_path TEXT,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES usuarios (id) ON DELETE CASCADE
        )
    ''')

    banco.commit()
    banco.close()

# Carregar o usuário antes de cada requisição
@app.before_request
def load_user():
    g.user = session.get('user')  # Carregar o usuário da sessão

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    if request.method == 'POST':
        try:
            nome = request.form['nome']
            sobrenome = request.form['sobrenome']
            telefone = request.form['telefone']
            cpf = request.form['cpf']
            email = request.form['email']
            senha = request.form['password']

            banco = get_db_connection()
            cursor = banco.cursor()
            cursor.execute('INSERT INTO usuarios (nome, sobrenome, telefone, cpf, email, senha) VALUES (?, ?, ?, ?, ?, ?)',
                           (nome, sobrenome, telefone, cpf, email, senha))
            banco.commit()
            flash("Usuário cadastrado com sucesso!", "success")
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash("Erro: CPF ou email já cadastrados.", "error")
        except sqlite3.Error as e:
            flash(f"Erro ao cadastrar: {e}", "error")
        finally:
            banco.close()

    return render_template('cadastro.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']

        banco = get_db_connection()
        cursor = banco.cursor()
        cursor.execute('SELECT * FROM usuarios WHERE email = ? AND senha = ?', (email, senha))
        usuario = cursor.fetchone()
        banco.close()

        if usuario:
            session['user_id'] = usuario['id']  # Armazena o ID do usuário na sessão
            session['user'] = usuario['nome']  # Armazena o nome do usuário na sessão
            flash("Login realizado com sucesso!", "success")
            return redirect(url_for('feed'))
        else:
            flash("Email ou senha incorretos.", "error")
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/feed')
def feed():
    if not g.user:
        return redirect(url_for('login'))  # Redireciona para login se o usuário não estiver autenticado

    banco = get_db_connection()
    cursor = banco.cursor()
    cursor.execute('SELECT posts.*, usuarios.nome FROM posts JOIN usuarios ON posts.user_id = usuarios.id ORDER BY timestamp DESC')
    posts = cursor.fetchall()  # Aqui pegamos todos os posts do banco
    banco.close()

    # Imprime os posts no console para verificar o formato
    print(posts)

    return render_template('feed.html', user=g.user, posts=posts)

@app.route('/nova_postagem', methods=['GET', 'POST'])
def nova_postagem():
    if 'user_id' not in session:
        return redirect(url_for('login'))  # Redireciona para login se o usuário não estiver autenticado

    if request.method == 'POST':
        content = request.form.get('post-content')  # Usando get para evitar KeyError
        image = request.files.get('post-image')

        # Verifica a extensão do arquivo
        if image and allowed_file(image.filename):
            # Extraindo o nome do arquivo
            filename = os.path.basename(image.filename)
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            os.makedirs(os.path.dirname(image_path), exist_ok=True)
            image.save(image_path)
        else:
            flash("Formato de imagem não permitido ou imagem não enviada.", "error")
            return redirect(url_for('nova_postagem'))

        timestamp = datetime.now().isoformat()
        banco = get_db_connection()
        cursor = banco.cursor()

        try:
            cursor.execute('INSERT INTO posts (user_id, content, image_path, timestamp) VALUES (?, ?, ?, ?)',
                           (session['user_id'], content, filename, timestamp))  # Salva apenas o nome do arquivo
            banco.commit()
            flash("Postagem criada com sucesso!", "success")
            return redirect(url_for('feed'))  # Redireciona para a página de feed após sucesso
        except sqlite3.Error as e:
            flash(f"Erro ao enviar a postagem: {e}", "error")
        finally:
            banco.close()

    return render_template('postagem.html')  # Use o template correto

@app.route('/postagem')
def postagem():
    return render_template('postagem.html')  # A nova rota que você pediu

@app.route('/perfil_usuario')
def perfil_usuario():
    if 'user_id' not in session:
        return redirect(url_for('login'))  # Redireciona para login se o usuário não estiver autenticado

    # Busca o perfil do usuário no banco de dados
    banco = get_db_connection()
    cursor = banco.cursor()
    cursor.execute('SELECT * FROM usuarios WHERE id = ?', (session['user_id'],))
    usuario = cursor.fetchone()
    banco.close()

    return render_template('perfil_usuario.html', usuario=usuario)  # Passa o perfil do usuário para o template

@app.route('/save-profile-image', methods=['POST'])
def save_profile_image():
    data = request.get_json()

    # Verifica se a imagem foi recebida
    if 'image' not in data:
        return jsonify({'success': False, 'message': 'Nenhuma imagem recebida.'}), 400
    
    # Decodifica a imagem base64
    image_data = data['image']
    image_data = image_data.split(",")[1]  # Remove o prefixo 'data:image/png;base64,'

    # Caminho para salvar a imagem de perfil
    profile_image_path = os.path.join(app.config['UPLOAD_FOLDER'], 'profile_image.png')

    # Verifica se a imagem tem uma extensão válida
    if not allowed_file(profile_image_path):
        return jsonify({'success': False, 'message': 'Formato de imagem não permitido.'}), 400

    # Salva a imagem em um arquivo
    try:
        with open(profile_image_path, 'wb') as img_file:
            img_file.write(base64.b64decode(image_data))
        
        # Atualiza o banco de dados com o caminho da imagem de perfil
        banco = get_db_connection()
        cursor = banco.cursor()
        cursor.execute('UPDATE usuarios SET profile_image = ? WHERE id = ?', (profile_image_path, session['user_id']))
        banco.commit()
        banco.close()

        return jsonify({'success': True, 'message': 'Imagem salva com sucesso!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/sobremim')
def sobremim():
    return render_template('sobremim.html')

@app.route('/logout')  # Nova rota de logout
def logout():
    session.pop('user_id', None)  # Remove o ID do usuário da sessão
    session.pop('user', None)  # Remove o nome do usuário da sessão
    flash("Você saiu com sucesso.", "success")
    return redirect(url_for('login'))

if __name__ == '__main__':
    init_db()  # Inicializa o banco de dados
    app.run(debug=True)
