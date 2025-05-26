import streamlit as st
import folium
from streamlit_folium import st_folium
from datetime import datetime
import uuid
import os
import json

DATA_FILE = "sensores.json"
PESSOAS_FILE = "pessoas.json"

def carregar_dados():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def salvar_dados(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4, default=str)

def carregar_pessoas():
    if os.path.exists(PESSOAS_FILE):
        with open(PESSOAS_FILE, "r") as f:
            return json.load(f)
    return []

def salvar_pessoas(pessoas):
    with open(PESSOAS_FILE, "w") as f:
        json.dump(pessoas, f, indent=4)

def calcular_status(proxima_data):
    dias_restantes = (datetime.strptime(proxima_data, "%Y-%m-%d") - datetime.now()).days
    if dias_restantes > 10:
        return "verde"
    elif 5 <= dias_restantes <= 10:
        return "amarelo"
    else:
        return "vermelho"

def mostrar_alertas(sensores):
    for sensor in sensores.values():
        manutencoes = sensor.get("manutencoes", [])
        if manutencoes:
            proximas = [m["proxima"] for m in manutencoes]
            proximas.sort()
            status = calcular_status(proximas[0])
            if status == "vermelho":
                st.warning(f"⚠️ SENSOR CRÍTICO: {sensor['nome']} - Manutenção urgente!")

st.set_page_config(layout="wide")
st.title("📍 Mapa de Sensores em Tempo Real")

# Carregar dados
sensores = carregar_dados()
pessoas = carregar_pessoas()
coordenadas_tefe = [-3.367, -64.716]
zoom_tefe = 12

# Menu lateral para escolher a área do app
area = st.sidebar.selectbox("Selecione a área do app:", ["Área de Sensores", "Gerenciar Responsáveis"])

if area == "Área de Sensores":

    mapa = folium.Map(location=coordenadas_tefe, zoom_start=zoom_tefe)

    for sensor_id, sensor in sensores.items():
        if "coordenadas" in sensor:
            cor = "blue"
            manutencoes = sensor.get("manutencoes", [])
            if manutencoes:
                proximas = [m["proxima"] for m in manutencoes]
                proximas.sort()
                status = calcular_status(proximas[0])
                if status == "amarelo":
                    cor = "orange"
                elif status == "vermelho":
                    cor = "red"
                else:
                    cor = "green"
            folium.Marker(
                location=sensor["coordenadas"],
                popup=sensor["nome"],
                icon=folium.Icon(color=cor)
            ).add_to(mapa)

    st_data = st_folium(mapa, width=1200, height=800)

    if "coord_clicada" not in st.session_state:
        st.session_state.coord_clicada = None
    if "sensor_selecionado" not in st.session_state:
        st.session_state.sensor_selecionado = None

    if st_data and st_data.get("last_clicked"):
        coords = st_data["last_clicked"]
        st.session_state.coord_clicada = (coords["lat"], coords["lng"])

    st.sidebar.header("Sensores Cadastrados")
    lista_sensores = [(sid, s["nome"]) for sid, s in sensores.items()]
    lista_sensores.sort(key=lambda x: x[1])

    opcoes = ["-- Nenhum --"] + [nome for _, nome in lista_sensores]
    selecionado_nome = st.sidebar.selectbox("Selecione um sensor para gerenciar:", opcoes)

    if selecionado_nome == "-- Nenhum --":
        st.session_state.sensor_selecionado = None
    else:
        for sid, nome in lista_sensores:
            if nome == selecionado_nome:
                st.session_state.sensor_selecionado = sid
                break

    st.sidebar.markdown("---")
    st.sidebar.markdown("## Cadastrar Novo Sensor")
    if st.session_state.coord_clicada:
        st.sidebar.write(f"Local clicado: {st.session_state.coord_clicada}")
        novo_nome = st.sidebar.text_input("Nome do novo sensor")
        if st.sidebar.button("Cadastrar sensor"):
            if novo_nome.strip() == "":
                st.sidebar.error("Informe um nome válido para o sensor.")
            else:
                novo_id = str(uuid.uuid4())
                sensores[novo_id] = {
                    "nome": novo_nome,
                    "coordenadas": list(st.session_state.coord_clicada),
                    "manutencoes": []
                }
                salvar_dados(sensores)
                st.sidebar.success(f"Sensor '{novo_nome}' cadastrado com sucesso!")
                st.session_state.sensor_selecionado = novo_id

    # Botão para excluir sensor selecionado
    if st.session_state.sensor_selecionado:
        if st.sidebar.button("Excluir sensor selecionado", key="btn_excluir_sensor"):
            nome_excluir = sensores[st.session_state.sensor_selecionado]["nome"]
            sensores.pop(st.session_state.sensor_selecionado)
            salvar_dados(sensores)
            st.sidebar.success(f"Sensor '{nome_excluir}' excluído com sucesso!")
            st.session_state.sensor_selecionado = None
            import sys
            sys.exit()

    st.write("## Detalhes do Sensor Selecionado")

    if st.session_state.sensor_selecionado and st.session_state.sensor_selecionado in sensores:
        sensor = sensores[st.session_state.sensor_selecionado]

        abas = ["Nova manutenção", "Ver status", "Histórico de manutenções"]
        aba = st.radio("Selecione uma aba:", abas, key="aba_sensor")

        if aba == "Nova manutenção":
            with st.form("form_manutencao"):
                descricao = st.text_area("Descrição da manutenção")
                data_hoje = datetime.now().strftime("%Y-%m-%d")
                data_proxima = st.date_input("Próxima manutenção")
                if pessoas:
                    responsavel = st.selectbox("Responsável pela manutenção", pessoas)
                else:
                    st.warning("Nenhum responsável cadastrado. Cadastre na área 'Gerenciar Responsáveis'.")
                    responsavel = None

                if st.form_submit_button("Salvar manutenção"):
                    if responsavel is None:
                        st.error("Selecione um responsável antes de salvar.")
                    elif descricao.strip() == "":
                        st.error("Informe a descrição da manutenção.")
                    else:
                        nova_manut = {
                            "data": data_hoje,
                            "descricao": descricao,
                            "proxima": data_proxima.strftime("%Y-%m-%d"),
                            "responsavel": responsavel
                        }
                        if "manutencoes" not in sensor:
                            sensor["manutencoes"] = []
                        sensor["manutencoes"].append(nova_manut)
                        salvar_dados(sensores)
                        st.success("Manutenção salva com sucesso!")

        elif aba == "Ver status":
            manutencoes = sensor.get("manutencoes", [])
            if manutencoes:
                ultima = sorted(manutencoes, key=lambda x: x["data"], reverse=True)[0]
                st.info(
                    f"Última manutenção: {ultima['data']}\n\n"
                    f"Descrição: {ultima['descricao']}\n\n"
                    f"Próxima: {ultima['proxima']}\n\n"
                    f"Responsável: {ultima.get('responsavel', 'Não informado')}"
                )
            else:
                st.warning("Nenhuma manutenção registrada.")

        elif aba == "Histórico de manutenções":
            manutencoes = sensor.get("manutencoes", [])
            if manutencoes:
                manutencoes_ordenadas = sorted(manutencoes, key=lambda x: x["data"], reverse=True)
                st.write(f"### Histórico de Manutenções ({len(manutencoes_ordenadas)})")
                for i, m in enumerate(manutencoes_ordenadas, 1):
                    st.markdown(
                        f"**{i}. Data:** {m['data']}  \n"
                        f"**Descrição:** {m['descricao']}  \n"
                        f"**Próxima manutenção:** {m['proxima']}  \n"
                        f"**Responsável:** {m.get('responsavel', 'Não informado')}"
                    )
                    btn_key = f"del_manut_{i}"
                    if st.button("Excluir", key=btn_key):
                        idx_original = sensor["manutencoes"].index(m)
                        sensor["manutencoes"].pop(idx_original)
                        salvar_dados(sensores)
                        st.success("Manutenção excluída com sucesso!")
                        import sys
                        sys.exit()
                    st.markdown("---")
            else:
                st.write("Nenhuma manutenção registrada até o momento.")

    else:
        st.write("Nenhum sensor selecionado.")

    mostrar_alertas(sensores)

elif area == "Gerenciar Responsáveis":
    # ----- Área para cadastrar, listar e excluir responsáveis -----
    st.header("Gerenciar Responsáveis")

    if pessoas:
        st.write("### Lista de Responsáveis")
        for i, pessoa in enumerate(pessoas, 1):
            col1, col2 = st.columns([8, 1])
            with col1:
                st.write(f"{i}. {pessoa}")
            with col2:
                btn_key = f"del_resp_{i}"
                if st.button("Excluir", key=btn_key):
                    pessoas.remove(pessoa)
                    salvar_pessoas(pessoas)
                    st.success(f"Responsável '{pessoa}' excluído com sucesso!")
                    import sys
                    sys.exit()
    else:
        st.write("Nenhum responsável cadastrado.")

    st.write("---")
    novo_resp = st.text_input("Nome do novo responsável")
    if st.button("Cadastrar responsável"):
        novo_resp = novo_resp.strip()
        if novo_resp == "":
            st.error("Informe um nome válido.")
        elif novo_resp in pessoas:
            st.warning("Esse responsável já está cadastrado.")
        else:
            pessoas.append(novo_resp)
            salvar_pessoas(pessoas)
            st.success(f"Responsável '{novo_resp}' cadastrado com sucesso!")
            import sys
            sys.exit()

st.sidebar.markdown("## 🔄 Atualize a página para atualizar os dados do mapa")
