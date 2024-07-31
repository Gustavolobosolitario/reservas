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

# Inicializa o cache de reservas
if 'reservas' not in st.session_state:
    st.session_state.reservas = []

if 'usuario_logado' not in st.session_state:
    st.session_state.usuario_logado = None


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
    
def limpar_banco_dados():
    conn = sqlite3.connect('reservas.db')
    cursor = conn.cursor()
    
    # Obtém a lista de todas as tabelas no banco de dados
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tabelas = cursor.fetchall()
    
    # Apaga todas as tabelas, exceto sqlite_sequence
    for tabela in tabelas:
        if tabela[0] != 'sqlite_sequence':  # Exclui sqlite_sequence da lista
            cursor.execute(f"DROP TABLE IF EXISTS {tabela[0]}")
    
    conn.commit()
    conn.close()
    st.success("Banco de dados limpo com sucesso!")



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

def criar_tabela_reservas():
    conn = sqlite3.connect('reservas.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS reservas (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        email_usuario TEXT,
                        data TEXT,
                        hora_inicio TEXT,
                        hora_fim TEXT,
                        placa TEXT,
                        cidade TEXT,
                        status TEXT)''')
    conn.commit()
    conn.close()

def adicionar_reserva(data, hora_inicio, hora_fim, placa, cidade):
    if veiculo_disponivel(data, hora_inicio, hora_fim, placa):
        conn = sqlite3.connect('reservas.db')
        cursor = conn.cursor()
        cursor.execute('INSERT INTO reservas (email_usuario, data, hora_inicio, hora_fim, placa, cidade, status) VALUES (?, ?, ?, ?, ?, ?, ?)',
                       (st.session_state.usuario_logado, data.strftime('%d/%m/%Y'), hora_inicio.strftime('%H:%M:%S'), hora_fim.strftime('%H:%M:%S'), placa, cidade, 'Agendado'))
        conn.commit()
        conn.close()
        return True
    return False

def atualizar_status_reserva(reserva_id, novo_status):
    conn = sqlite3.connect('reservas.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE reservas SET status = ? WHERE id = ?', (novo_status, reserva_id))
    conn.commit()
    conn.close()
    return cursor.rowcount > 0  # Retorna True se a atualização for bem-sucedida, caso contrário, False





def exibir_reservas(pagina='todas'):
    conn = sqlite3.connect('reservas.db')
    query = 'SELECT * FROM reservas'
    if pagina == 'minhas' and st.session_state.usuario_logado:
        query += ' WHERE email_usuario = ?'
        df_reservas = pd.read_sql_query(query, conn, params=(st.session_state.usuario_logado,))
    else:
        df_reservas = pd.read_sql_query(query, conn)
    conn.close()
    
    if 'status' in df_reservas.columns:
        st.dataframe(estilizar_reservas(df_reservas), use_container_width=True)
    else:
        st.dataframe(df_reservas, use_container_width=True)



def veiculo_disponivel(data, hora_inicio, hora_fim, placa):
    # Converte os horários para objetos datetime para comparação
    data_hora_inicio = datetime.combine(data, hora_inicio)
    data_hora_fim = datetime.combine(data, hora_fim)
    
    for reserva in st.session_state.reservas:
        reserva_data = datetime.strptime(reserva['data'], '%d/%m/%Y').date()
        reserva_hora_inicio = datetime.strptime(reserva['hora_inicio'], '%H:%M:%S').time()
        reserva_hora_fim = datetime.strptime(reserva['hora_fim'], '%H:%M:%S').time()
        reserva_data_hora_inicio = datetime.combine(reserva_data, reserva_hora_inicio)
        reserva_data_hora_fim = datetime.combine(reserva_data, reserva_hora_fim)
        
        if reserva['placa'] == placa and reserva['status'] == 'Concluído':
            # Verifica sobreposição de reservas
            if (data_hora_inicio < reserva_data_hora_fim and reserva_data_hora_inicio < data_hora_fim):
                return False
    return True


# Função para adicionar uma reserva
def adicionar_reserva(data, hora_inicio, hora_fim, placa, cidade):
    if veiculo_disponivel(data, hora_inicio, hora_fim, placa):
        reserva_id = len(st.session_state.reservas) + 1
        st.session_state.reservas.append({
            'id': reserva_id,
            'email_usuario': st.session_state.usuario_logado,
            'data': data.strftime('%d/%m/%Y'),
            'hora_inicio': hora_inicio.strftime('%H:%M:%S'),
            'hora_fim': hora_fim.strftime('%H:%M:%S'),
            'placa': placa,
            'cidade': cidade,
            'status': 'Agendado'
        })
        return True
    return False

# Função para atualizar o status de uma reserva
def atualizar_status_reserva(reserva_id, novo_status):
    for reserva in st.session_state.reservas:
        if reserva['id'] == reserva_id:
            reserva['status'] = novo_status
            return True
    return False

# Função para atualizar o status da reserva
def atualizar_status_reserva(reserva_id, novo_status):
    # Implementar lógica para atualizar o status da reserva
    pass

#

# Função para atualizar o status da reserva
def atualizar_status_reserva(reserva_id, novo_status):
    # Implementar lógica para atualizar o status da reserva
    # Retorna True se a atualização for bem-sucedida, caso contrário, False
    pass

# Função para alterar o status de uma reserva
def alterar_status_reserva():
    st.header('Alterar Status de Reserva')

    if st.session_state.usuario_logado:
        # Cria um DataFrame com as reservas do usuário
        df_reservas = pd.DataFrame(st.session_state.reservas)
        if not df_reservas.empty:
            reserva_id = st.selectbox('Selecione a Reserva para Alterar', df_reservas['id'])
            
            # Encontra a reserva selecionada
            reserva = df_reservas[df_reservas['id'] == reserva_id].iloc[0]
            
            # Cria 3 colunas
            col1, col2, col3 = st.columns(3)
            
            # Adiciona widgets em cada coluna
            with col1:
                st.write(f"Detalhes da Reserva Selecionada:")
                st.write(f"Data: {reserva['data']}")
            
            with col2:
                st.write(f"Hora Reserva: {reserva['hora_inicio']}")
                st.write(f"Hora Entrega: {reserva['hora_fim']}")
            
            with col3:
                st.write(f"Descrição Veículo: {reserva['placa']}")
                st.write(f"Cidades: {reserva['cidade']}")
                st.write(f"Status Atual: {reserva['status']}")
            
            novo_status = st.selectbox('Novo Status', ['Agendado', 'Cancelado', 'Concluído'])

            if st.button('Atualizar Status'):
                sucesso = atualizar_status_reserva(reserva_id, novo_status)
                if sucesso:
                    st.success('Status atualizado com sucesso!')
                    st.experimental_rerun()  # Recarrega a página para atualizar a lista de reservas
                else:
                    st.error('Erro ao atualizar o status da reserva.')
        else:
            st.write('Você não possui reservas para alterar.')
    else:
        st.error('Você precisa estar logado para alterar o status da reserva.')


# Função para estilizar reservas
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

# Função de atualização do status da reserva
def atualizar_status_reserva(reserva_id, novo_status):
    # Função para atualizar o status da reserva no banco de dados ou na lista de reservas
    # Exemplo fictício de atualização
    reservas = st.session_state.reservas
    for reserva in reservas:
        if reserva['id'] == reserva_id:
            reserva['status'] = novo_status
            return True
    return False

# CSS para remover ícones de âncoras e links
css = """
<style>
/* Remove o ícone de âncora ao lado dos cabeçalhos */
[data-anchor-id] {
    display: none;
}

/* Remove a âncora do cabeçalho */
a[href^="#"] {
    display: none;
}
</style>
"""

        
        
# Função para exibir todas as reservas
def exibir_reservas_todas():
    if 'reservas' in st.session_state:
        df_reservas = pd.DataFrame(st.session_state.reservas)
        
       
        


# Função para exibir reservas
def exibir_reservas(pagina='todas'):
    df_reservas = pd.DataFrame(st.session_state.reservas)
    
    if pagina == 'minhas':
        if st.session_state.usuario_logado:
            df_reservas = df_reservas[df_reservas['email_usuario'] == st.session_state.usuario_logado]
        else:
            st.error('Você precisa estar logado para ver suas reservas.')
            return
    
    if 'status' in df_reservas.columns:
        st.dataframe(estilizar_reservas(df_reservas), use_container_width=True)
    else:
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
status_opcoes = ['Agendado', 'Cancelado', 'Concluído']



def home_page():
    st.markdown(css, unsafe_allow_html=True)
    
    if st.session_state.usuario_logado:
        
        # Seção para limpar banco de dados
        st.sidebar.header('Administração')
        if st.sidebar.button('Limpar Banco de Dados'):
            limpar_banco_dados()
            st.experimental_rerun()  # Recarrega a página para refletir as alterações

        st.header("Reservar Veículo")
        
        
        # Cria colunas para os formulários
        with st.form(key='form_principal'):
            col1, col2 = st.columns(2)

            with col1:
                # Dados de Retirada
                data_retirada = st.date_input('Retirada', value=datetime.now())
                hora_retirada = st.time_input( '',value=datetime(2024, 1, 1, 9, 0).time())
                
                # Atualiza o session_state diretamente
                st.session_state.data_retirada = data_retirada
                st.session_state.hora_retirada = hora_retirada

            with col2:
                # Dados de Devolução
                data_devolucao = st.date_input('Devolução', value=datetime.now())
                hora_devolucao = st.time_input('', value=datetime(2024, 1, 1, 9, 30).time())
                
                # Atualiza o session_state diretamente
                st.session_state.data_devolucao = data_devolucao
                st.session_state.hora_devolucao = hora_devolucao

            # Dados Adicionais e Adicionar Reserva
            
            col1, col2 = st.columns(2)
            
            with col1:
                cidade = st.selectbox('', cidades)
            
            with col2:
                placa = st.selectbox('', placas)
                submit_button_adicional = st.form_submit_button(label='Adicionar Reserva')
            
            if submit_button_adicional:
                hora_inicio = arredondar_para_intervalo(st.session_state.hora_retirada)
                hora_fim = arredondar_para_intervalo(st.session_state.hora_devolucao)
                sucesso = adicionar_reserva(st.session_state.data_retirada, hora_inicio, hora_fim, placa, cidade)
                
                if sucesso:
                    st.success('Reserva adicionada com sucesso!')
                else:
                    st.error('Veículo não disponível para o horário selecionado.')

        # Seção: Todas as Reservas
        # Seção: Todas as Reservas
        st.header('Todas as Reservas')
        
        exibir_reservas(pagina='todas')
        
        # Seção: Minhas Reservas
        st.header('Minhas Reservas')
        exibir_reservas(pagina='minhas')

        # Seção: Alterar Status de Reserva
        st.header('Alterar Status de Reserva')
        with st.form(key='alterar_status_form'):
            col1, col2, = st.columns(2)
            
            with col1:
                reserva_id = st.number_input('ID da Reserva', min_value=1)
                
                
            with col2:
                novo_status = st.selectbox('Novo Status', status_opcoes)
            
            submit_button = st.form_submit_button(label='Atualizar Status')
            if submit_button:
                sucesso = atualizar_status_reserva(reserva_id, novo_status)
                if sucesso:
                    st.success('Status atualizado com sucesso!')
                    exibir_reservas(pagina='todas')  # Atualiza a exibição para refletir o novo status
                else:
                    st.error('Reserva não encontrada.')
                    
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
