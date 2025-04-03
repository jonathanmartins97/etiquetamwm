import streamlit as st
import datetime
import tempfile
import os
from PIL import Image, ImageDraw, ImageFont
from pylibdmtx.pylibdmtx import encode
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import mm
import sys

# Função para determinar se está em um sistema Windows
def is_windows():
    return sys.platform.startswith('win')

# Função para obter impressoras no Windows
def get_printers():
    try:
        import win32print
        printers = [printer[2] for printer in win32print.EnumPrinters(
            win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
        )]
        return printers if printers else None
    except ImportError:
        return None

# Função para selecionar impressora
def select_printer():
    printers = get_printers()
    if not printers:
        st.warning("Nenhuma impressora encontrada.")
        return None
    return st.selectbox("Selecione a Impressora:", printers)

def load_font(font_name, size):
    try:
        return ImageFont.truetype(font_name, size)
    except IOError:
        return ImageFont.load_default()

def create_label_image(data_fabricacao, part_number, nivel_liberacao, serial_fabricacao, nf, logo_path, dpi=300, logo_position=(10, 10), text_offset=-30):
    label_width, label_height = 110, 85 # mm (largura x altura na vertical)
    width_pixels, height_pixels = (int(label_width * dpi / 25.4), int(label_height * dpi / 25.4))

    # Criando imagem na vertical
    img = Image.new('RGB', (width_pixels, height_pixels), color='white')
    draw = ImageDraw.Draw(img)
    
    font_title = load_font("arialbd.ttf", 45)  # Fonte negrito para títulos
    font_data = load_font("calibri.ttf", 40)  # Fonte regular para dados
    font_code = load_font("arialbd.ttf", 50)  # Fonte para o código PR020 abaixo do DataMatrix
    
    # Carregar a imagem do logo
    logo = Image.open(logo_path)
    logo = logo.resize((500, 120))  # Ajuste conforme necessário
    img.paste(logo, logo_position)
    y_pos = logo_position[1] + logo.size[1] + text_offset  # Posição do primeiro texto
    
    # Lista de informações formatadas
    info_texts = [
        ("Data de Fabricação:", data_fabricacao.strftime('%d/%m/%Y')),
        ("Part Number MWM:", part_number),
        ("Nível de Liberação:", nivel_liberacao),
        ("Serial de Fabricação:", serial_fabricacao),
        ("Identificação do Fornecedor:", "13785"),
        ("Número da NF:", nf),
    ]
    
    for title, value in info_texts:
        draw.text((650, y_pos), title, fill="black", font=font_title)
        y_pos += 45  # Espaço entre título e valor
        draw.text((650, y_pos), value, fill="black", font=font_data)
        y_pos += 65  # Avança para a próxima linha
    
    # Criar e posicionar o código DataMatrix
    dm_data = f"{data_fabricacao.strftime('%d/%m/%Y')};{part_number};{nivel_liberacao};{serial_fabricacao};13785;{nf}"
    datamatrix = encode(dm_data.encode('utf-8'))
    dm_img = Image.frombytes('RGB', (datamatrix.width, datamatrix.height), datamatrix.pixels)
    dm_img = dm_img.resize((600, 400))  # Ajustando tamanho

    dm_x, dm_y = 5, 200  # Posição do DataMatrix
    img.paste(dm_img, (dm_x, dm_y))

    # Adicionar o código "PR020" abaixo do DataMatrix
    pr020_x = dm_x + dm_img.width // 2
    pr020_y = dm_y + dm_img.height + 20
    draw.text((pr020_x, pr020_y), PR_datamatrix, fill="black", font=font_code, anchor="mm")

    # **Rotacionar a imagem para horizontal**
    img = img.rotate(90, expand=True)  # Rotaciona 90 graus no sentido horário

    return img

def save_as_pdf(img, quantity):
    pdf_path = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False).name
    c = canvas.Canvas(pdf_path, pagesize=(150*mm, 100*mm))
    
    img_path = tempfile.NamedTemporaryFile(suffix=".png", delete=False).name
    img.save(img_path, format="PNG")
    
    for _ in range(quantity):
        c.drawImage(img_path, 0, 0, width=110*mm, height=85*mm)
        c.showPage()
    
    c.save()
    os.remove(img_path)
    return pdf_path

def print_pdf(pdf_path):
    if is_windows():
        try:
            import win32api
            win32api.ShellExecute(0, "print", pdf_path, None, ".", 0)
            st.success("Etiqueta(s) enviada(s) para impressão!")
        except Exception as e:
            st.error(f"Erro ao imprimir: {str(e)}")
    else:
        st.warning("Impressão automática não suportada neste ambiente. Faça o download e imprima manualmente.")
        st.download_button(label="Baixar PDF para Impressão", data=open(pdf_path, "rb").read(), file_name="etiqueta.pdf", mime="application/pdf")

# Dicionário para preenchimento automático
dados_mwm = {
    "7000448C93": {"nivel": "A", "serial": "13785", "datamatrix":"PR019"},
    "7000666C93": {"nivel": "A", "serial": "13785", "datamatrix":"PR018"},
    "961201150166": {"nivel": "A", "serial": "13785", "datamatrix":"PR020"},
    "7000449C3": {"nivel": "A", "serial": "13785", "datamatrix":"PR023"},
}

st.title("Etiquetas MWM")
printer_name = select_printer()
data_fabricacao = st.date_input("Data de Fabricação", datetime.date.today())
data_formatada = data_fabricacao.strftime("%d/%m/%Y")
part_number = st.selectbox("Part Number MWM:", list(dados_mwm.keys()))

# Preenchimento automático
nivel_liberacao = st.text_input("Nível de Liberação:", value=dados_mwm[part_number]["nivel"])
serial_fabricacao = st.text_input("Serial de Fabricação:", value=dados_mwm[part_number]["serial"])
PR_datamatrix = st.text_input("cod datamatrix", value=dados_mwm[part_number]["datamatrix"])

nf = st.text_input("Número da Nota Fiscal (NF):")
quantidade = st.number_input("Quantidade de Etiquetas:", min_value=1, value=1, step=1)

if getattr(sys, 'frozen', False):
    logo_path = os.path.join(sys._MEIPASS, "logoPMK.png")
else:
     logo_path = "C:\\python\\logoPMK.png"


if st.button("Visualizar Prévia"):
    img_preview = create_label_image(data_fabricacao, part_number, nivel_liberacao, serial_fabricacao, nf, logo_path)
    st.image(img_preview, caption="Prévia da Etiqueta", width=500)

if st.button("Salvar como PDF"):
    img_pdf = create_label_image(data_fabricacao, part_number, nivel_liberacao, serial_fabricacao, nf, logo_path)
    pdf_path = save_as_pdf(img_pdf, quantidade)
    with open(pdf_path, "rb") as f:
        st.download_button(label="Baixar PDF", data=f, file_name="etiqueta.pdf", mime="application/pdf")

if st.button("Imprimir Etiqueta"):
    img_pdf = create_label_image(data_fabricacao, part_number, nivel_liberacao, serial_fabricacao, nf, logo_path)
    pdf_path = save_as_pdf(img_pdf, quantidade)
    print_pdf(pdf_path)
