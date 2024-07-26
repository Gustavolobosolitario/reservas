import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import pytz
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import sqlite3
import hashlib
import matplotlib.pyplot as plt

st.set_page_config(layout='wide', page_title="Sistema de Reservas", page_icon=":car:")

# Configurações de e-mail
EMAIL_ADDRESS = 'seuemail@gmail.com'
EMAIL_PASSWORD = 'suasenha'

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

# Funções para gerenciar o banco de dados
def criar_tabela_usuarios():
    conn = sqlite3.connect('reservas.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS usuarios (
                        id INTEGER PRIMARY KEY,
                        email TEXT UNIQUE,
                        senha TEXT)''')
    conn.commit()
    conn.close()

def adicionar_usuario(email, senha):
    conn = sqlite3.connect('reservas.db')
    cursor = conn.cursor()
    senha_hash = hashlib.sha256(senha.encode()).hexdigest()
    try:
        cursor.execute('INSERT INTO usuarios (email, senha) VALUES (?, ?)', (email, senha_hash))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False

def verificar_usuario(email, senha):
    conn = sqlite3.connect('reservas.db')
    cursor = conn.cursor()
    senha_hash = hashlib.sha256(senha.encode()).hexdigest()
    cursor.execute('SELECT * FROM usuarios WHERE email = ? AND senha = ?', (email, senha_hash))
    usuario = cursor.fetchone()
    conn.close()
    return usuario

def atualizar_senha(email, nova_senha):
    conn = sqlite3.connect('reservas.db')
    cursor = conn.cursor()
    senha_hash = hashlib.sha256(nova_senha.encode()).hexdigest()
    cursor.execute('UPDATE usuarios SET senha = ? WHERE email = ?', (senha_hash, email))
    conn.commit()
    conn.close()

# Inicializa o cache de reservas
if 'reservas' not in st.session_state:
    st.session_state.reservas = []

if 'usuario_logado' not in st.session_state:
    st.session_state.usuario_logado = None

# Funções de autenticação
def login():
    st.markdown('<div style="background-color:#f0f2f6;padding:20px;border-radius:8px;">', unsafe_allow_html=True)
    st.subheader('Login')
    email = st.text_input('E-mail', placeholder='Digite seu e-mail')
    senha = st.text_input('Senha', type='password', placeholder='Digite sua senha')
    if st.button('Entrar'):
        if verificar_usuario(email, senha):
            st.session_state.usuario_logado = email
            st.success('Login bem-sucedido!')
            st.experimental_rerun()
        else:
            st.error('E-mail ou senha incorretos.')
    st.markdown('</div>', unsafe_allow_html=True)

def cadastro():
    st.markdown('<div style="background-color:#f0f2f6;padding:20px;border-radius:8px;">', unsafe_allow_html=True)
    st.subheader('Cadastro')
    email = st.text_input('E-mail', placeholder='Digite seu e-mail')
    senha = st.text_input('Senha', type='password', placeholder='Digite sua senha')
    confirmar_senha = st.text_input('Confirme a Senha', type='password', placeholder='Confirme sua senha')
    if st.button('Cadastrar'):
        if senha == confirmar_senha:
            if adicionar_usuario(email, senha):
                st.success('Cadastro realizado com sucesso!')
                st.experimental_rerun()
            else:
                st.error('E-mail já cadastrado.')
        else:
            st.error('As senhas não correspondem.')
    st.markdown('</div>', unsafe_allow_html=True)

def recuperar_senha():
    st.markdown('<div style="background-color:#f0f2f6;padding:20px;border-radius:8px;">', unsafe_allow_html=True)
    st.subheader('Recuperar Senha')
    email = st.text_input('E-mail', placeholder='Digite seu e-mail')
    if st.button('Enviar link de recuperação'):
        nova_senha = 'senha123'  # Idealmente, gere uma senha aleatória ou forneça um link para redefinição
        atualizar_senha(email, nova_senha)
        enviar_email(email, 'Recuperação de Senha', f'Sua nova senha é: {nova_senha}')
        st.success('E-mail de recuperação enviado!')
    st.markdown('</div>', unsafe_allow_html=True)

def arredondar_para_intervalo(time_obj, intervalo_mins=30):
    total_mins = time_obj.hour * 60 + time_obj.minute
    arredondado = round(total_mins / intervalo_mins) * intervalo_mins
    horas = arredondado // 60
    minutos = arredondado % 60
    return datetime.strptime(f"{horas:02}:{minutos:02}:00", '%H:%M:%S').time()

def veiculo_disponivel(data, hora_inicio, hora_fim, placa):
    for reserva in st.session_state.reservas:
        if reserva['data'] == data and reserva['placa'] == placa and reserva['status'] == 'Concluído':
            if ((reserva['hora_inicio'] < hora_inicio < reserva['hora_fim']) or
                (reserva['hora_inicio'] < hora_fim < reserva['hora_fim']) or
                (hora_inicio <= reserva['hora_inicio'] and hora_fim >= reserva['hora_fim'])):
                return False
    return True

# Função para adicionar reserva
def adicionar_reserva(data, hora_inicio, hora_fim, placa, cidade):
    data_str = data.strftime('%Y-%m-%d')
    hora_inicio_str = hora_inicio.strftime('%H:%M:%S')
    hora_fim_str = hora_fim.strftime('%H:%M:%S')
    
    if veiculo_disponivel(data_str, hora_inicio_str, hora_fim_str, placa):
        reserva_id = len(st.session_state.reservas) + 1
        st.session_state.reservas.append({
            'id': reserva_id,
            'email_usuario': st.session_state.usuario_logado,  # Usando o e-mail do usuário
            'data': data_str,
            'hora_inicio': hora_inicio_str,
            'hora_fim': hora_fim_str,
            'placa': placa,
            'cidade': cidade,
            'status': 'Concluído'
        })
        return True
    return False

def atualizar_status_reserva(reserva_id, novo_status):
    for reserva in st.session_state.reservas:
        if reserva['id'] == reserva_id:
            reserva['status'] = novo_status
            return True
    return False


def estilizar_reservas(df):
    def cor_status(status):
        if status == 'Agendado':
            return 'background-color: yellow'
        elif status == 'Cancelado':
            return 'background-color: red; color: white'
        elif status == 'Concluído':
            return 'background-color: green; color: white'
        else:
            return ''

    return df.style.applymap(cor_status, subset=['status'])

def exibir_reservas(pagina='todas'):
    df_reservas = pd.DataFrame(st.session_state.reservas)
    
    if pagina == 'minhas':
        if st.session_state.usuario_logado:
            df_reservas = df_reservas[df_reservas['email_usuario'] == st.session_state.usuario_logado]
        else:
            st.error('Você precisa estar logado para ver suas reservas.')
            return
    
    st.dataframe(df_reservas, use_container_width=True)

def plotar_grafico_barras():
    df_reservas = pd.DataFrame(st.session_state.reservas)
    df_veiculos = df_reservas['placa'].value_counts().reset_index()
    df_veiculos.columns = ['Placa', 'Quantidade']

    fig, ax = plt.subplots()
    ax.bar(df_veiculos['Placa'], df_veiculos['Quantidade'])
    ax.set_xlabel('Placa do Veículo')
    ax.set_ylabel('Quantidade de Reservas')
    ax.set_title('Quantidade de Reservas por Veículo')

    st.pyplot(fig)

# Listas de placas e cidades
placas = ['SWQ1F92 - Nissan Versa Novo', 'SVO6A16 - Saveiro', 'GEZ5262 - Nissan Versa']
cidades = ['Rio Claro', 'Lençóis Paulista', 'São Carlos', 'Araras', 'Ribeirão Preto', 'Jaboticabal', 'Araraquara', 'Leme', 'Piracicaba' ,'São Paulo' ,'Campinas', 'Ibate', 'Porto Ferreira']
status_opcoes = ['Concluído', 'Cancelado', 'Agendado']

def home_page():
    st.title('Sistema de Reservas de Veículos')

    if st.session_state.usuario_logado:
        menu = st.sidebar.radio('Menu', ['Reservar Veículo', 'Minhas Reservas', 'Alterar Status'])

        if menu == 'Reservar Veículo':
            with st.sidebar:
                st.subheader('Reservar Veículo')
                data = st.date_input('Data da Reserva')
                hora_inicio = st.time_input('Hora Início', value=datetime(2024, 1, 1, 9, 0).time())
                hora_fim = st.time_input('Hora Fim', value=datetime(2024, 1, 1, 9, 30).time())
                placa = st.selectbox('Placa do Veículo', placas)
                cidade = st.selectbox('Cidade', cidades)
                
                if st.button('Adicionar Reserva'):
                    hora_inicio = arredondar_para_intervalo(hora_inicio)
                    hora_fim = arredondar_para_intervalo(hora_fim)
                    sucesso = adicionar_reserva(data, hora_inicio, hora_fim, placa, cidade)
                    if sucesso:
                        st.success('Reserva adicionada com sucesso!')
                    else:
                        st.error('Veículo não disponível para o horário selecionado.')
            
            st.subheader('Reservas Atuais')
            exibir_reservas(pagina='todas')
        
        elif menu == 'Minhas Reservas':
            st.subheader('Minhas Reservas')
            exibir_reservas(pagina='minhas')
        
        elif menu == 'Alterar Status':
            with st.container():
                st.subheader('Alterar Status de Reserva')
                reserva_id = st.number_input('ID da Reserva', min_value=1)
                novo_status = st.selectbox('Novo Status', status_opcoes)
                
                if st.button('Atualizar Status'):
                    sucesso = atualizar_status_reserva(reserva_id, novo_status)
                    if sucesso:
                        st.success('Status atualizado com sucesso!')
                        exibir_reservas(pagina='todas')  # Atualiza a exibição para refletir o novo status
                    else:
                        st.error('Reserva não encontrada.')

            st.subheader('Gráfico de Reservas por Veículo')
            plotar_grafico_barras()
    
    else:
        st.sidebar.subheader('Autenticação')
        menu_autenticacao = st.sidebar.radio('Menu', ['Login', 'Cadastro', 'Recuperar Senha'])
        
        if menu_autenticacao == 'Login':
            login()
        
        elif menu_autenticacao == 'Cadastro':
            cadastro()
        
        elif menu_autenticacao == 'Recuperar Senha':
            recuperar_senha()

# Cria a tabela de usuários se não existir
criar_tabela_usuarios()

# Executa a página inicial
home_page()
