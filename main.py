from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.image import Image
from kivy.uix.scrollview import ScrollView
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.graphics import Color, Rectangle, RoundedRectangle
from kivy_garden.mapview import MapView, MapMarker
import os
import requests
from kivy.clock import Clock
import shutil
import fitz  # PyMuPDF
from kivy.graphics.texture import Texture
import glob
from kivy.factory import Factory

class PDFReader:
    def __init__(self, pdf_path):
        self.pdf_path = pdf_path
        self.doc = None
        self.total_pages = 0
        self.current_page = 0
        
    def open_pdf(self):
        try:
            self.doc = fitz.open(self.pdf_path)
            self.total_pages = len(self.doc)
            return True
        except Exception as e:
            print(f"Erro ao abrir PDF: {e}")
            return False
    
    def get_page_texture(self, page_num, zoom=2.0):
        if not self.doc or page_num < 0 or page_num >= self.total_pages:
            return None
            
        try:
            page = self.doc.load_page(page_num)
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)
            
            img_data = pix.tobytes("raw", "RGB")
            texture = Texture.create(size=(pix.width, pix.height), colorfmt='rgb')
            texture.blit_buffer(img_data, colorfmt='rgb', bufferfmt='ubyte')
            
            return texture
        except Exception as e:
            print(f"Erro ao renderizar página {page_num}: {e}")
            return None
    
    def close(self):
        if self.doc:
            self.doc.close()

class RoundedButton(Button):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_color = (0, 0, 0, 0)
        self.background_normal = ''
        self.bind(pos=self.update_canvas, size=self.update_canvas)
    
    def update_canvas(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(0.89, 0.75, 0.58, 1)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[15])

class ImageButton(Button):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_color = (0, 0, 0, 0)
        self.background_normal = ''

class MainScreen(Screen):
    pass

class MapSelectionScreen(Screen):
    pass

class BookMapScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.map_view = None
        Clock.schedule_once(self.init_book_map, 0.5)
    
    def init_book_map(self, dt):
        if self.map_view:
            self.ids.map_container.remove_widget(self.map_view)
        
        self.map_view = MapView(
            zoom=7, 
            lat=-3.7300, 
            lon=-38.5000,
            size_hint=(1, 1)
        )
        self.ids.map_container.add_widget(self.map_view)
        
        book_locations = {
            'Fortaleza': (-3.7300, -38.5000),
            'Jaguaribe': (-5.8939, -38.6222),
            'Aquiraz': (-3.9019, -38.3919)
        }
        
        for name, (lat, lon) in book_locations.items():
            marker = MapMarker(lat=lat, lon=lon)
            marker.name = name
            self.map_view.add_widget(marker)
            marker.bind(on_release=lambda instance, m=marker: self.on_book_marker_click(m))
    
    def on_book_marker_click(self, marker):
        app = App.get_running_app()
        app.set_previous_screen('book_map')
        app.show_location_detail('book', marker.name.lower().replace(' ', '_'))

class AuthorMapScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.map_view = None
        Clock.schedule_once(self.init_author_map, 0.5)
    
    def init_author_map(self, dt):
        if self.map_view:
            self.ids.map_container.remove_widget(self.map_view)
        
        self.map_view = MapView(
            zoom=4, 
            lat=-15.7801, 
            lon=-47.9292,
            size_hint=(1, 1)
        )
        self.ids.map_container.add_widget(self.map_view)
        
        author_locations = {
            'Messejana': (-3.8319, -38.4567),
            'Rio de Janeiro': (-22.9068, -43.1729),
            'São Paulo': (-23.5505, -46.6333)
        }
        
        for name, (lat, lon) in author_locations.items():
            marker = MapMarker(lat=lat, lon=lon)
            marker.name = name
            self.map_view.add_widget(marker)
            marker.bind(on_release=lambda instance, m=marker: self.on_author_marker_click(m))
    
    def on_author_marker_click(self, marker):
        app = App.get_running_app()
        app.set_previous_screen('author_map')
        app.show_location_detail('author', marker.name.lower().replace(' ', '_'))

class LocationDetailScreen(Screen):
    def set_location_data(self, location_data):
        self.ids.location_title.text = location_data['name']
        self.ids.location_desc.text = location_data['description']
        self.ids.location_reference.text = location_data['reference']
        if 'image' in location_data:
            self.ids.location_image.source = location_data['image']
        else:
            self.ids.location_image.source = ''

class AboutScreen(Screen):
    pass

class ReaderScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.pdf_reader = None
        self.current_page = 0
        self.total_pages = 0
        self.page_zoom = 2.0
        
    def on_enter(self):
        Clock.schedule_once(self.init_reader, 0.1)
    
    def init_reader(self, dt):
        pdf_path = self.find_pdf_file()
        
        if not pdf_path:
            self.show_error("Nenhum arquivo PDF do livro foi encontrado.")
            return
        
        try:
            self.load_pdf(pdf_path)
        except Exception as e:
            self.show_error(f"Erro ao carregar o livro: {str(e)}")
    
    def find_pdf_file(self):
        possible_names = [
            "Iracema-Jose-de-Alenquer.pdf",
            "Iracema_José_de_Alencar.pdf",
            "Iracema.pdf",
            "iracema.pdf"
        ]
        
        for name in possible_names:
            if os.path.exists(name):
                return name
        
        pdf_files = glob.glob("**/*.pdf", recursive=True)
        if pdf_files:
            for pdf in pdf_files:
                if "iracema" in pdf.lower():
                    return pdf
            return pdf_files[0]
        
        return None
    
    def load_pdf(self, pdf_path):
        if self.pdf_reader:
            self.pdf_reader.close()
        
        self.pdf_reader = PDFReader(pdf_path)
        
        if not self.pdf_reader.open_pdf():
            raise Exception("Não foi possível abrir o arquivo PDF")
        
        self.total_pages = self.pdf_reader.total_pages
        self.current_page = 0
        self.update_page_display()
    
    def update_page_display(self):
        self.ids.reader_container.clear_widgets()
        
        if not self.pdf_reader:
            return
            
        texture = self.pdf_reader.get_page_texture(self.current_page, self.page_zoom)
        
        if texture:
            page_image = Image(
                texture=texture,
                size_hint=(None, None),
                allow_stretch=True,
                keep_ratio=True
            )
            
            self.adjust_image_size(page_image, texture.size)
            self.ids.reader_container.add_widget(page_image)
        
        self.ids.page_label.text = f"Página {self.current_page + 1} de {self.total_pages}"
    
    def adjust_image_size(self, image, texture_size):
        screen_width = Window.width - 40
        screen_height = Window.height - 200
        
        img_width, img_height = texture_size
        ratio = img_width / img_height
        
        if img_width > screen_width or img_height > screen_height:
            if screen_width / screen_height > ratio:
                new_height = screen_height
                new_width = new_height * ratio
            else:
                new_width = screen_width
                new_height = new_width / ratio
            
            image.size = (new_width, new_height)
        else:
            image.size = texture_size
        
        image.pos_hint = {'center_x': 0.5, 'center_y': 0.5}
    
    def next_page(self):
        if self.pdf_reader and self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.update_page_display()
    
    def prev_page(self):
        if self.pdf_reader and self.current_page > 0:
            self.current_page -= 1
            self.update_page_display()
    
    def zoom_in(self):
        self.page_zoom = min(4.0, self.page_zoom + 0.5)
        self.update_page_display()
    
    def zoom_out(self):
        self.page_zoom = max(0.5, self.page_zoom - 0.5)
        self.update_page_display()
    
    def show_error(self, message):
        content = BoxLayout(orientation='vertical', padding=10, spacing=10)
        content.add_widget(Label(text=message))
        btn = Button(text='OK', size_hint_y=None, height=40)
        popup = Popup(title='Erro', content=content, size_hint=(0.7, 0.4))
        btn.bind(on_press=popup.dismiss)
        content.add_widget(btn)
        popup.open()
    
    def on_leave(self):
        if self.pdf_reader:
            self.pdf_reader.close()

class IracemaApp(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.previous_screen = 'main'
    
    def build(self):
        # Registrar classes personalizadas no Factory
        Factory.register('RoundedButton', cls=RoundedButton)
        Factory.register('ImageButton', cls=ImageButton)
        
        self.sm = ScreenManager()
        self.sm.add_widget(MainScreen(name='main'))
        self.sm.add_widget(MapSelectionScreen(name='map_selection'))
        self.sm.add_widget(BookMapScreen(name='book_map'))
        self.sm.add_widget(AuthorMapScreen(name='author_map'))
        self.sm.add_widget(LocationDetailScreen(name='location_detail'))
        self.sm.add_widget(AboutScreen(name='about'))
        self.sm.add_widget(ReaderScreen(name='reader'))
        return self.sm

    def set_previous_screen(self, screen_name):
        self.previous_screen = screen_name

    def download_book(self):
        try:
            source_path = r"Iracema-Jose-de-Alenquer.pdf"
            filename = "Iracema_José_de_Alencar.pdf"
            
            if not os.path.exists(source_path):
                raise FileNotFoundError(f"Arquivo não encontrado: {source_path}")

            shutil.copy(source_path, filename)
            
            self.show_popup("Download Concluído", 
                          f"O livro foi salvo como:\n{filename}\n\nLocal: {os.path.abspath(filename)}")
            
        except Exception as e:
            self.show_popup("Erro", f"Ocorreu um erro ao tentar fazer o download: {str(e)}")
    
    def show_popup(self, title, message):
        content = BoxLayout(orientation='vertical', padding=10, spacing=10)
        content.add_widget(Label(text=message, text_size=(Window.width * 0.6, None)))
        btn = Button(text='OK', size_hint_y=None, height=40)
        popup = Popup(title=title, content=content, size_hint=(0.8, 0.6))
        btn.bind(on_press=popup.dismiss)
        content.add_widget(btn)
        popup.open()

    def show_location_detail(self, location_type, location_id):
        locations_data = {
            'book': {
                'fortaleza': {
                    'name': 'Fortaleza - CE',
                    'description': '''Fortaleza é mencionada diversas vezes em Iracema como a terra dos colonizadores portugueses. Na época da história, era um importante ponto de comércio e colonização.

Contexto Histórico:
• Fundação: 1726 (como vila)
• Importância: Principal centro urbano do Ceará
• Papel no livro: Representa o mundo europeu em contraste com o mundo indígena

No romance, Fortaleza simboliza a civilização europeia que se expandia pelo território brasileiro, contrastando com o mundo natural e indígena representado por Iracema.''',
                    'reference': '"A virgem dos lábios de mel" - referência à Iracema como representação da terra cearense',
                    'image': r'/home/migs/Documentos/migs/programing/Iracema/Iracema-windows/img/fortaleza.jpg'
                },
                'jaguaribe': {
                    'name': 'Rio Jaguaribe',
                    'description': '''O Rio Jaguaribe é um importante cenário natural no livro Iracema, representando a natureza brasileira em seu estado puro.

Características:
• Maior rio totalmente cearense
• Percorre mais de 600 km
• Foi vital para as tribos indígenas

No livro, o Jaguaribe representa a fluidez da vida e a conexão entre as diferentes tribos e personagens. Suas margens testemunham encontros e desencontros entre Iracema e Martim.''',
                    'reference': '"As águas do Jaguaribe testemunharam o amor proibido" - Capítulo 4',
                    'image': r'/home/migs/Documentos/migs/programing/Iracema/Iracema-windows/img/jaguaribe.jpg'
                },
                'aquiraz': {
                    'name': 'Aquiraz - CE',
                    'description': '''Aquiraz foi a primeira capital do Ceará e aparece no contexto histórico do romance.

Dados históricos:
• Primeira capital: 1799 a 1823
• Localização: Litoral leste do Ceará
• Importância: Centro administrativo colonial

No contexto de Iracema, Aquiraz representa a administração portuguesa e o processo de colonização que afetou diretamente as tribos indígenas da região.''',
                    'reference': '"Na antiga capital, os destinos se cruzaram" - Capítulo 7',
                    'image': r'/home/migs/Documentos/migs/programing/Iracema/Iracema-windows/img/aquiraz.jpg'
                }
            },
            'author': {
                'messejana': {
                    'name': 'Messejana - CE',
                    'description': '''Messejana, hoje bairro de Fortaleza, foi o local de nascimento de José de Alencar.

Dados biográficos:
• Nascimento: 1º de maio de 1829
• Família: Pertencente à elite cearense
• Contexto: Ambiente urbano em formação

Esta localidade influenciou profundamente a visão de mundo do autor, que mesmo vivendo posteriormente no Rio de Janeiro, manteve fortes laços com suas origens cearenses.''',
                    'reference': '"Da minha terra natal trouxe as cores para pintar Iracema" - José de Alencar',
                    'image': r'/home/migs/Documentos/migs/programing/Iracema/Iracema-windows/img/messejana.jpg'
                },
                'rio_de_janeiro': {
                    'name': 'Rio de Janeiro - RJ',
                    'description': '''O Rio de Janeiro foi onde José de Alencar desenvolveu grande parte de sua carreira literária e política.

Atuação no Rio:
• Advogado e jornalista
• Deputado e ministro da Justiça
• Intelectual influente

Foi no Rio que Alencar escreveu Iracema, demonstrando sua saudade e idealização do Ceará, criando assim uma imagem romantizada de sua terra natal.''',
                    'reference': '"No Rio, longe do Ceará, nasceu a mais cearense das histórias"',
                    'image': r'/home/migs/Documentos/migs/programing/Iracema/Iracema-windows/img/rio.png'
                },
                'são_paulo': {
                    'name': 'São Paulo - SP',
                    'description': '''São Paulo foi importante na formação intelectual de José de Alencar.

Formação:
• Estudou Direito no Largo de São Francisco
• Convívio com a elite intelectual paulista
• Período de amadurecimento literário

Sua passagem por São Paulo contribuiu para sua formação como um dos principais escritores do Romantismo brasileiro, influenciando sua visão sobre a construção da identidade nacional.''',
                    'reference': '"Os anos em São Paulo moldaram o jurista que seria romancista"',
                    'image': r'/home/migs/Documentos/migs/programing/Iracema/Iracema-windows/img/sao_paulo.jpg'
                }
            }
        }
        
        location = locations_data[location_type][location_id]
        detail_screen = self.sm.get_screen('location_detail')
        detail_screen.set_location_data(location)
        self.sm.current = 'location_detail'

    def go_back(self):
        if hasattr(self, 'previous_screen'):
            self.sm.current = self.previous_screen
        else:
            self.sm.current = 'main'

if __name__ == '__main__':
    IracemaApp().run()