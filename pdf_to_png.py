import fitz  # PyMuPDF, imported as fitz for backward compatibility reasons
file_path = r"E:\trabalho_livro_iracema\final\livro\Iracema - Jose de Alenquer.pdf" # caminho para o arquivo PDF de entrada
doc = fitz.open(file_path)  # open document
for i, page in enumerate(doc):
    pix = page.get_pixmap()  # render page to an image
    pix.save(f"page_{i}.png")