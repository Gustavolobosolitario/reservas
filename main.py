import streamlit as st
import pandas as pd
from datetime import datetime, time
import sqlite3
import hashlib
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

st.set_page_config(layout='wide', page_title="Sistema de Reservas", page_icon=":car:")

# Inicializa o cache de reservas
if 'reservas' not in st.session_state:
    st.session_state.reservas = []

if 'usuario_logado' not in st.session_state:
    st.session_state.usuario_logado = None

if 'pagina' not in st.session_state:
    st.session_state.pagina = 'home'

# Configurações de e-mail
EMAIL_ADDRESS = os.getenv('EMAIL_ADDRESS', 'seuemail@gmail.com')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD', 'suasenha')

def enviar_email(to_email, subject, body):
    msg = MIMEMultipart()
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.sendmail(EMAIL_ADDRESS, to_email, msg.as_string())
        st.success("E-mail enviado com sucesso!")
    except smtplib.SMTPAuthenticationError as e:
        st.error(f"Erro de autenticação: {e}")

def login():
    st.markdown('', unsafe_allow_html=True)
    st.subheader('Login')
    email = st.text_input('E-mail', placeholder='Digite seu e-mail')
    senha = st.text_input('Senha', type='password', placeholder='Digite sua senha')
    if st.button('Entrar'):
        if verificar_usuario(email, senha):
            st.session_state.usuario_logado = email
            st.success('Login bem-sucedido!')
            st.session_state.pagina = 'home'
        else:
            st.error('E-mail ou senha incorretos.')
    st.markdown('</div>', unsafe_allow_html=True)

def cadastro():
    st.markdown('', unsafe_allow_html=True)
    st.subheader('Cadastro')
    email = st.text_input('E-mail', placeholder='Digite seu e-mail')
    senha = st.text_input('Senha', type='password', placeholder='Digite sua senha')
    confirmar_senha = st.text_input('Confirme a Senha', type='password', placeholder='Confirme sua senha')
    if st.button('Cadastrar'):
        if senha == confirmar_senha:
            if adicionar_usuario(email, senha):
                st.success('Cadastro realizado com sucesso!')
            else:
                st.error('E-mail já cadastrado.')
        else:
            st.error('As senhas não correspondem.')
    st.markdown('</div>', unsafe_allow_html=True)

def recuperar_senha():
    st.markdown('', unsafe_allow_html=True)
    st.subheader('Recuperar Senha')
    email = st.text_input('E-mail', placeholder='Digite seu e-mail')
    if st.button('Enviar link de recuperação'):
        nova_senha = 'senha123'  # Idealmente, gere uma senha aleatória ou forneça um link para redefinição
        atualizar_senha(email, nova_senha)
        enviar_email(email, 'Recuperação de Senha', f'Sua nova senha é: {nova_senha}')
        st.success('E-mail de recuperação enviado!')
    st.markdown('</div>', unsafe_allow_html=True)

def criar_tabela_usuarios():
    with sqlite3.connect('reservas.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS usuarios (
                            id INTEGER PRIMARY KEY,
                            email TEXT UNIQUE,
                            senha TEXT)''')
        conn.commit()

def criar_tabela_reservas():
    with sqlite3.connect('reservas.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS reservas (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            email_usuario TEXT,
                            dtRetirada TEXT,
                            dtDevolucao TEXT,
                            hrRetirada TEXT,
                            hrDevolucao TEXT,
                            carro TEXT,
                            cidade TEXT,
                            status TEXT)''')
        conn.commit()

def adicionar_usuario(email, senha):
    senha_hash = hashlib.sha256(senha.encode()).hexdigest()
    try:
        with sqlite3.connect('reservas.db') as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT INTO usuarios (email, senha) VALUES (?, ?)', (email, senha_hash))
            conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False

def verificar_usuario(email, senha):
    senha_hash = hashlib.sha256(senha.encode()).hexdigest()
    with sqlite3.connect('reservas.db') as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM usuarios WHERE email = ? AND senha = ?', (email, senha_hash))
        return cursor.fetchone()

def atualizar_senha(email, nova_senha):
    senha_hash = hashlib.sha256(nova_senha.encode()).hexdigest()
    with sqlite3.connect('reservas.db') as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE usuarios SET senha = ? WHERE email = ?', (senha_hash, email))
        conn.commit()

def arredondar_para_intervalo(time_obj, intervalo_mins=30):
    total_mins = time_obj.hour * 60 + time_obj.minute
    arredondado = round(total_mins / intervalo_mins) * intervalo_mins
    horas = arredondado // 60
    minutos = arredondado % 60
    return time(horas, minutos)

def adicionar_reserva(dtRetirada, hrRetirada, dtDevolucao, hrDevolucao, carro, destino):
    if veiculo_disponivel(dtRetirada, hrRetirada, dtDevolucao, hrDevolucao, carro):
        with sqlite3.connect('reservas.db') as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT INTO reservas (email_usuario, dtRetirada, hrRetirada, dtDevolucao, hrDevolucao, carro, cidade, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                           (st.session_state.usuario_logado, dtRetirada.strftime('%d/%m/%Y'), hrRetirada.strftime('%H:%M:%S'), dtDevolucao.strftime('%d/%m/%Y'), hrDevolucao.strftime('%H:%M:%S'), carro, destino, 'Agendado'))
            conn.commit()
        return True
    return False

def atualizar_status_reserva(reserva_id, novo_status):
    with sqlite3.connect('reservas.db') as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE reservas SET status = ? WHERE id = ?', (novo_status, reserva_id))
        conn.commit()
        return cursor.rowcount > 0

def estilizar_reservas(df):
    def aplicar_estilo(status):
        if status == 'Agendado':
            return ['background-color: yellow']*len(df.columns)
        elif status == 'Em andamento':
            return ['background-color: lightblue']*len(df.columns)
        elif status == 'Concluído':
            return ['background-color: lightgreen']*len(df.columns)
        elif status == 'Cancelado':
            return ['background-color: red']*len(df.columns)
        else:
            return ['']*len(df.columns)
    return df.style.apply(lambda x: aplicar_estilo(x['status']), axis=1)


def carregar_reservas_do_banco():
    with sqlite3.connect('reservas.db') as conn:
        query = 'SELECT * FROM reservas'
        df_reservas = pd.read_sql_query(query, conn)
    return df_reservas

def exibir_reservas(pagina='todas'):
    df_reservas = carregar_reservas_do_banco()
    
    if pagina == 'minhas' and st.session_state.usuario_logado:
        if 'email_usuario' in df_reservas.columns:
            df_reservas = df_reservas[df_reservas['email_usuario'] == st.session_state.usuario_logado]
        else:
            st.error("Coluna 'email_usuario' não encontrada no DataFrame.")
    
    if 'status' in df_reservas.columns:
        st.dataframe(estilizar_reservas(df_reservas), use_container_width=True)
    else:
        st.dataframe(df_reservas, use_container_width=True)

def veiculo_disponivel(dtRetirada, hrRetirada, dtDevolucao, hrDevolucao, carro):
    """
    Verifica se o veículo está disponível para o intervalo de tempo fornecido,
    considerando também o status da reserva.

    :param dtRetirada: Data da retirada (datetime.date)
    :param hrRetirada: Hora da retirada (datetime.time)
    :param dtDevolucao: Data da devolução (datetime.date)
    :param hrDevolucao: Hora da devolução (datetime.time)
    :param carro: Placa do veículo (str)
    :return: True se o veículo estiver disponível, False caso contrário
    """
    data_inicio = datetime.combine(dtRetirada, hrRetirada)
    data_fim = datetime.combine(dtDevolucao, hrDevolucao)

    with sqlite3.connect('reservas.db') as conn:
        query = """
        SELECT dtRetirada, hrRetirada, dtDevolucao, hrDevolucao, status
        FROM reservas
        WHERE carro = ?
        """
        df_reservas = pd.read_sql_query(query, conn, params=(carro,))

    for _, row in df_reservas.iterrows():
        reserva_data_inicio = datetime.strptime(f"{row['dtRetirada']} {row['hrRetirada']}", '%d/%m/%Y %H:%M:%S')
        reserva_data_fim = datetime.strptime(f"{row['dtDevolucao']} {row['hrDevolucao']}", '%d/%m/%Y %H:%M:%S')

        if row['status'] != 'Cancelado' and not (data_fim <= reserva_data_inicio or data_inicio >= reserva_data_fim):
            return False
    return True


def verificar_status_reserva(data_reserva, hora_inicio, hora_fim, carro):
    """
    Verifica se o veículo está reservado para uma data e hora específicas.
    
    :param data_reserva: Data da reserva (datetime.date)
    :param hora_inicio: Hora de início da reserva (datetime.time)
    :param hora_fim: Hora de fim da reserva (datetime.time)
    :param carro: Carro (str)
    :return: Status da reserva (str)
    """
    dtRetirada_str = data_reserva.strftime('%d/%m/%Y')
    hrRetirada_str = hora_inicio.strftime('%H:%M:%S')
    hrDevolucao_str = hora_fim.strftime('%H:%M:%S')

    with sqlite3.connect('reservas.db') as conn:
        cursor = conn.cursor()
        query = """
        SELECT status FROM reservas
        WHERE carro = ? AND dtRetirada = ? AND (hrRetirada <= ? AND hrDevolucao >= ?)
        """
        cursor.execute(query, (carro, dtRetirada_str, hrDevolucao_str, hrRetirada_str))
        reserva = cursor.fetchone()

    if reserva:
        return reserva[0]  # Retorna o status da reserva
    else:
        return "Nenhuma reserva encontrada para esse veículo e horário."

def limpar_banco_dados():
    try:
        with sqlite3.connect('reservas.db') as conn:
            cursor = conn.cursor()
            cursor.execute("DROP TABLE IF EXISTS reservas;")
            cursor.execute("DROP TABLE IF EXISTS usuarios;")
            conn.commit()
            criar_tabela_reservas()
            criar_tabela_usuarios()
    except sqlite3.OperationalError as e:
        st.error(f"Erro ao acessar o banco de dados: {e}")

def home_page():
    criar_tabela_usuarios()
    criar_tabela_reservas()
    
    # Adiciona o logo à barra lateral
    st.sidebar.image('logo.png', use_column_width=True)  # Atualize o caminho para o logo conforme necessário

    st.markdown(css, unsafe_allow_html=True)

    if st.session_state.get('usuario_logado'):
        st.sidebar.header('Administração')
        if st.sidebar.button('Limpar Banco de Dados'):
            limpar_banco_dados()
            st.experimental_rerun()

        with st.container(border=True):
            st.title('Reserva')

            col1, col2 = st.columns(2)

            with col1:
                st.text('Retirada')
                dtRetirada = st.date_input(label='Data de Retirada', key='dtRetirada', value=datetime.now(), label_visibility='hidden')
                hrRetirada = st.time_input(label='', key='hrRetirada', value=time(9, 0))

            with col2:
                st.text('Devolução')
                dtDevolucao = st.date_input(label='Data de Devolução', key='dtDevolucao', value=datetime.now(), label_visibility='hidden')
                hrDevolucao = st.time_input(label='', key='hrDevolucao', value=time(9, 0))

            descVeiculo = st.selectbox(label='Carro', key='carro', options=[
                'SWQ1F92 - Nissan Versa Novo', 'SVO6A16 - Saveiro', 'GEZ5262 - Nissan Versa'
            ])
            descDestino = st.selectbox(label='Cidade', key='destino', options=[
                'Rio Claro', 'Lençóis Paulista', 'São Carlos', 'Araras', 'Ribeirão Preto',
                'Jaboticabal', 'Araraquara', 'Leme', 'Piracicaba', 'São Paulo',
                'Campinas', 'Ibate', 'Porto Ferreira'
            ])

            if st.button(label='Cadastrar'):
                dados = {
                    'dtRetirada': dtRetirada,
                    'hrRetirada': hrRetirada,
                    'dtDevolucao': dtDevolucao,
                    'hrDevolucao': hrDevolucao,
                    'carro': descVeiculo,
                    'destino': descDestino
                }
                st.success('Reserva cadastrada com sucesso!')
                st.json(dados)

                # Adicione a reserva ao banco de dados
                if veiculo_disponivel(dtRetirada, hrRetirada, dtDevolucao, hrDevolucao, descVeiculo):
                    if adicionar_reserva(dtRetirada, hrRetirada, dtDevolucao, hrDevolucao, descVeiculo, descDestino):
                        st.success('Reserva registrada no banco de dados com sucesso!')
                    else:
                        st.error('Falha ao registrar a reserva.')
                else:
                    st.error('O veículo já está reservado para o horário selecionado.')

        with st.form(key='alterar_status_form'):
            col1, col2 = st.columns(2)

            with col1:
                reserva_id = st.number_input('ID da Reserva', min_value=1)

            with col2:
                novo_status = st.selectbox('Novo Status', ['Agendado', 'Em andamento', 'Concluído', 'Cancelado'])

            submit_button = st.form_submit_button(label='Atualizar Status')
            if submit_button:
                sucesso = atualizar_status_reserva(reserva_id, novo_status)
                if sucesso:
                    st.success('Status atualizado com sucesso!')
                    exibir_reservas(pagina='todas')
                else:
                    st.error('Reserva não encontrada.')
                    
        if st.button('Ver todas as reservas'):
            st.session_state.pagina = 'reservas'
            st.experimental_set_query_params(pagina='reservas')

    else:
        st.sidebar.subheader('')
        menu_autenticacao = st.sidebar.radio('', ['Login', 'Cadastro', 'Recuperar Senha'])

        if menu_autenticacao == 'Login':
            login()
        elif menu_autenticacao == 'Cadastro':
            cadastro()
        elif menu_autenticacao == 'Recuperar Senha':
            recuperar_senha()

css = """
<style>
/* Adicione seu CSS personalizado aqui */
</style>
"""

if st.session_state.pagina == 'home':
    home_page()
elif st.session_state.pagina == 'reservas':
    st.title('Todas as Reservas')
    exibir_reservas(pagina='todas')
    if st.button('Voltar'):
        st.session_state.pagina = 'home'
        st.experimental_set_query_params(pagina='home')
