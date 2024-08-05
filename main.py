import streamlit as st
import pandas as pd
from datetime import datetime, time
import sqlite3
import hashlib
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

# Configura a página do Streamlit
st.set_page_config(layout='wide', page_title="Sistema de Reservas", page_icon=":car:")

# Inicializa o cache de reservas se não existir
if 'reservas' not in st.session_state:
    st.session_state.reservas = []

# Inicializa a variável de controle de usuário logado
if 'usuario_logado' not in st.session_state:
    st.session_state.usuario_logado = None

# Inicializa a variável de controle da página atual
if 'pagina' not in st.session_state:
    st.session_state.pagina = 'home'

# Configurações de e-mail
EMAIL_ADDRESS = os.getenv('EMAIL_ADDRESS', 'seuemail@gmail.com')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD', 'suasenha')

# Função para enviar e-mails
def enviar_email(to_email, subject, body):
    # Cria uma mensagem multipart
    msg = MIMEMultipart()
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    # Tenta enviar o e-mail
    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()  # Inicia TLS para segurança
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)  # Login no servidor SMTP
            server.sendmail(EMAIL_ADDRESS, to_email, msg.as_string())  # Envia o e-mail
        st.success("E-mail enviado com sucesso!")
    except smtplib.SMTPAuthenticationError as e:
        st.error(f"Erro de autenticação: {e}")

# Função de login
def login():
    st.markdown('', unsafe_allow_html=True)
    st.subheader('Login')
    email = st.text_input('E-mail', placeholder='Digite seu e-mail')
    senha = st.text_input('Senha', type='password', placeholder='Digite sua senha')
    if st.button('Entrar'):
        if verificar_usuario(email, senha):  # Verifica as credenciais do usuário
            st.session_state.usuario_logado = email  # Define o usuário como logado
            st.success('Login bem-sucedido!')
            st.session_state.pagina = 'home'  # Navega para a página inicial
        else:
            st.error('E-mail ou senha incorretos.')

# Função de cadastro
def cadastro():
    st.markdown('<div style="background-color:#f0f2f6;padding:20px;border-radius:8px;">', unsafe_allow_html=True)
    st.subheader('Cadastro')
    email = st.text_input('E-mail', placeholder='Digite seu e-mail')
    senha = st.text_input('Senha', type='password', placeholder='Digite sua senha')
    confirmar_senha = st.text_input('Confirme a Senha', type='password', placeholder='Confirme sua senha')
    if st.button('Cadastrar'):
        if senha == confirmar_senha:  # Verifica se as senhas coincidem
            if adicionar_usuario(email, senha):  # Tenta adicionar o usuário
                st.success('Cadastro realizado com sucesso!')
            else:
                st.error('E-mail já cadastrado.')
        else:
            st.error('As senhas não correspondem.')
    st.markdown('</div>', unsafe_allow_html=True)

# Função de recuperação de senha
def recuperar_senha():
    st.markdown('<div style="background-color:#f0f2f6;padding:20px;border-radius:8px;">', unsafe_allow_html=True)
    st.subheader('Recuperar Senha')
    email = st.text_input('E-mail', placeholder='Digite seu e-mail')
    if st.button('Enviar link de recuperação'):
        nova_senha = 'senha123'  # Idealmente, gere uma senha aleatória ou forneça um link para redefinição
        atualizar_senha(email, nova_senha)  # Atualiza a senha no banco de dados
        enviar_email(email, 'Recuperação de Senha', f'Sua nova senha é: {nova_senha}')
        st.success('E-mail de recuperação enviado!')
    st.markdown('</div>', unsafe_allow_html=True)

# Função para criar a tabela de usuários
def criar_tabela_usuarios():
    with sqlite3.connect('reservas.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS usuarios (
                            id INTEGER PRIMARY KEY,
                            email TEXT UNIQUE,
                            senha TEXT)''')
        conn.commit()

# Função para criar a tabela de reservas
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

# Função para adicionar um novo usuário
def adicionar_usuario(email, senha):
    senha_hash = hashlib.sha256(senha.encode()).hexdigest()  # Criptografa a senha
    try:
        with sqlite3.connect('reservas.db') as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT INTO usuarios (email, senha) VALUES (?, ?)', (email, senha_hash))
            conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False

# Função para verificar as credenciais do usuário
def verificar_usuario(email, senha):
    senha_hash = hashlib.sha256(senha.encode()).hexdigest()  # Criptografa a senha
    with sqlite3.connect('reservas.db') as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM usuarios WHERE email = ? AND senha = ?', (email, senha_hash))
        return cursor.fetchone()

# Função para atualizar a senha do usuário
def atualizar_senha(email, nova_senha):
    senha_hash = hashlib.sha256(nova_senha.encode()).hexdigest()  # Criptografa a nova senha
    with sqlite3.connect('reservas.db') as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE usuarios SET senha = ? WHERE email = ?', (senha_hash, email))
        conn.commit()

# Função para arredondar a hora para o intervalo mais próximo
def arredondar_para_intervalo(time_obj, intervalo_mins=30):
    total_mins = time_obj.hour * 60 + time_obj.minute  # Calcula o total de minutos
    arredondado = round(total_mins / intervalo_mins) * intervalo_mins  # Arredonda para o intervalo mais próximo
    horas = arredondado // 60
    minutos = arredondado % 60
    return time(horas, minutos)

# Função para adicionar uma nova reserva
def adicionar_reserva(dtRetirada, hrRetirada, dtDevolucao, hrDevolucao, carro, destino):
    if veiculo_disponivel(dtRetirada, hrRetirada, dtDevolucao, hrDevolucao, carro):
        with sqlite3.connect('reservas.db') as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT INTO reservas (email_usuario, dtRetirada, hrRetirada, dtDevolucao, hrDevolucao, carro, cidade, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                           (st.session_state.usuario_logado, dtRetirada.strftime('%d/%m/%Y'), hrRetirada.strftime('%H:%M:%S'), dtDevolucao.strftime('%d/%m/%Y'), hrDevolucao.strftime('%H:%M:%S'), carro, destino, 'Agendado'))
            conn.commit()
        return True
    return False

# Função para atualizar o status de uma reserva
def atualizar_status_reserva(reserva_id, novo_status):
    with sqlite3.connect('reservas.db') as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE reservas SET status = ? WHERE id = ?', (novo_status, reserva_id))
        conn.commit()
        return cursor.rowcount > 0

# Função para estilizar a visualização de reservas com base no status
def estilizar_reservas(df):
    def aplicar_estilo(status):
        if status == 'Agendado':
            return ['background-color: yellow']*len(df.columns)
        elif status == 'Em andamento':
            return ['background-color: lightblue']*len(df.columns)
        elif status == 'Concluído':
            return ['background-color: lightgreen']*len(df.columns)
        else:
            return ['']*len(df.columns)
    return df.style.apply(lambda x: aplicar_estilo(x['status']), axis=1)

# Função para carregar reservas do banco de dados
def carregar_reservas_do_banco():
    with sqlite3.connect('reservas.db') as conn:
        query = 'SELECT * FROM reservas'
        df_reservas = pd.read_sql_query(query, conn)
    return df_reservas

# Função para filtrar reservas com base em critérios específicos
def filtrar_reservas(df, dtRetirada=None, dtDevolucao=None, carros=None, cidades=None):
    if dtRetirada:
        df = df[df['dtRetirada'] == pd.Timestamp(dtRetirada).strftime('%d/%m/%Y')]
    
    if dtDevolucao:
        df = df[df['dtDevolucao'] == pd.Timestamp(dtDevolucao).strftime('%d/%m/%Y')]
    
    if carros:
        df = df[df['carro'].str.contains('|'.join(carros), case=False, na=False)]
    
    if cidades:
        df = df[df['cidade'].str.contains('|'.join(cidades), case=False, na=False)]
    
    return df

# Função para buscar reservas aplicando filtros
def buscar_reservas_filtros(dtRetirada=None, dtDevolucao=None, carros=None, cidade=None):
    df_reservas = carregar_reservas_do_banco()
    return filtrar_reservas(df_reservas, dtRetirada, dtDevolucao, carros, cidade)

# Função para criar DataFrame formatado para visualização
def criar_df_para_visualizacao(df):
    df['dtRetirada'] = pd.to_datetime(df['dtRetirada'], format='%d/%m/%Y')
    df['dtDevolucao'] = pd.to_datetime(df['dtDevolucao'], format='%d/%m/%Y')
    df['hrRetirada'] = pd.to_datetime(df['hrRetirada'], format='%H:%M:%S').dt.time
    df['hrDevolucao'] = pd.to_datetime(df['hrDevolucao'], format='%H:%M:%S').dt.time
    return df

# Função para visualizar reservas na interface
def visualizar_reservas():
    st.markdown('<div style="background-color:#f0f2f6;padding:20px;border-radius:8px;">', unsafe_allow_html=True)
    st.subheader('Visualizar Reservas')

    # Formulário para filtrar reservas
    with st.form(key='filtros'):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            dtRetirada = st.date_input('Data de Retirada')
        with col2:
            dtDevolucao = st.date_input('Data de Devolução')
        with col3:
            carro = st.text_input('Carro')
        with col4:
            cidade = st.text_input('Cidade')

        filtro_aplicado = st.form_submit_button('Buscar')

    if filtro_aplicado:
        df_filtrada = buscar_reservas_filtros(dtRetirada, dtDevolucao, carro, cidade)
        df_filtrada = criar_df_para_visualizacao(df_filtrada)
        st.write(estilizar_reservas(df_filtrada))

    st.markdown('</div>', unsafe_allow_html=True)

# Função para verificar se o veículo está disponível
def veiculo_disponivel(dtRetirada, hrRetirada, dtDevolucao, hrDevolucao, carro):
    df_reservas = carregar_reservas_do_banco()
    df_reservas['dtRetirada'] = pd.to_datetime(df_reservas['dtRetirada'], format='%d/%m/%Y')
    df_reservas['dtDevolucao'] = pd.to_datetime(df_reservas['dtDevolucao'], format='%d/%m/%Y')
    df_reservas['hrRetirada'] = pd.to_datetime(df_reservas['hrRetirada'], format='%H:%M:%S').dt.time
    df_reservas['hrDevolucao'] = pd.to_datetime(df_reservas['hrDevolucao'], format='%H:%M:%S').dt.time

    for index, row in df_reservas.iterrows():
        if row['carro'] == carro:
            # Converte dtRetirada e dtDevolucao para o mesmo formato de row['dtRetirada'] e row['dtDevolucao']
            dtRetirada_ts = pd.Timestamp(dtRetirada)
            dtDevolucao_ts = pd.Timestamp(dtDevolucao)
            
            if dtRetirada_ts <= row['dtDevolucao'] and dtDevolucao_ts >= row['dtRetirada']:
                if (hrRetirada >= row['hrRetirada'] and hrRetirada <= row['hrDevolucao']) or \
                   (hrDevolucao >= row['hrRetirada'] and hrDevolucao <= row['hrDevolucao']) or \
                   (hrRetirada <= row['hrRetirada'] and hrDevolucao >= row['hrDevolucao']):
                    return False
    return True

# Função para exibir reservas na interface
def exibir_reservas(pagina='todas'):
    df_reservas = carregar_reservas_do_banco()
    if pagina == 'minhas' and st.session_state.usuario_logado:
        df_reservas = df_reservas[df_reservas['email_usuario'] == st.session_state.usuario_logado]
    st.dataframe(estilizar_reservas(df_reservas) if 'status' in df_reservas.columns else df_reservas, use_container_width=True)

# Função para verificar o status de uma reserva específica
def verificar_status_reserva(data_reserva, hora_inicio, hora_fim, carro):
    dtRetirada_str = data_reserva.strftime('%d/%m/%Y')
    hrRetirada_str = hora_inicio.strftime('%H:%M:%S')
    hrDevolucao_str = hora_fim.strftime('%H:%M:%S')

    with sqlite3.connect('reservas.db') as conn:
        cursor = conn.cursor()
        query = """
        SELECT status FROM reservas
        WHERE carro = ? AND dtRetirada = ? AND (hrRetirada <= ? AND hrDevolucao >= ?)
        """
        cursor.execute(query, (carro, dtRetirada_str, hrRetirada_str, hrDevolucao_str))
        reserva = cursor.fetchone()

    return reserva[0] if reserva else "Nenhuma reserva encontrada para esse veículo e horário."

# Função para limpar o banco de dados
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

# Função para exibir a página inicial
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
                dtRetirada = st.date_input(label='Data de Retirada', key='dtRetirada_filtro', value=None, label_visibility='visible')

            with col2:
                dtDevolucao = st.date_input(label='Data de Devolução', key='dtDevolucao_filtro', value=None, label_visibility='visible')

            col3, col4 = st.columns(2)

            with col3:
                carro = st.multiselect(label='Carro', key='carro_filtro', options=['SWQ1F92 - Nissan Versa Novo', 'SVO6A16 - Saveiro', 'GEZ5262 - Nissan Versa'])

            with col4:
                cidade = st.multiselect(label='Cidade', key='cidade_filtro', options=['Rio Claro', 'Lençóis Paulista', 'São Carlos', 'Araras', 'Ribeirão Preto',
                'Jaboticabal', 'Araraquara', 'Leme', 'Piracicaba', 'São Paulo','Campinas', 'Ibate', 'Porto Ferreira'])

            submit_button = st.form_submit_button(label='Buscar')
            if submit_button:
                df_reservas = buscar_reservas_filtros(dtRetirada, dtDevolucao, carro, cidade)
                if df_reservas.empty:
                    st.error('Nenhuma reserva encontrada.')
                else:
                    df_selecao = criar_df_para_visualizacao(df_reservas)
                    st.dataframe(df_selecao)

                    reserva_id = st.selectbox('Selecionar Reserva', df_selecao['id'].values)
                    reserva_selecionada = df_selecao[df_reservas['id'] == reserva_id]

                    st.write('Detalhes da Reserva Selecionada:')
                    st.write(reserva_selecionada)

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

# Navegação entre páginas
if st.session_state.pagina == 'home':
    home_page()
elif st.session_state.pagina == 'reservas':
    st.title('Todas as Reservas')
    exibir_reservas(pagina='todas')
    if st.button('Voltar'):
        st.session_state.pagina = 'home'
        st.experimental_set_query_params(pagina='home')
