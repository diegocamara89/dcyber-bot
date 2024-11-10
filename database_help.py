# database_help.py
from database_manager import db

def criar_tabela_ajuda():
    """Cria a tabela de tópicos de ajuda"""
    queries = [
        '''
        CREATE TABLE IF NOT EXISTS help_topics (
            id SERIAL PRIMARY KEY,
            codigo TEXT UNIQUE NOT NULL,
            titulo TEXT NOT NULL,
            conteudo TEXT NOT NULL,
            ordem INTEGER DEFAULT 0
        )
        ''',
        '''
        CREATE TABLE IF NOT EXISTS help_views (
            id SERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL,
            topic_id BIGINT NOT NULL,
            viewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (topic_id) REFERENCES help_topics (id)
        )
        '''
    ]
    
    for query in queries:
        db.execute_query(query)

def inicializar_topicos_ajuda():
    """Inicializa os tópicos de ajuda padrão"""
    topicos = [
        ('geral', 'Ajuda Geral', AJUDA_GERAL, 1),
        ('assinaturas', 'Assinaturas', AJUDA_ASSINATURAS, 2),
        ('casos', 'Casos', AJUDA_CASOS, 3),
        ('contatos', 'Contatos', AJUDA_CONTATOS, 4),
        ('lembretes', 'Lembretes', AJUDA_LEMBRETES, 5)
    ]
    
    for codigo, titulo, conteudo, ordem in topicos:
        db.execute_query(
            '''
            INSERT OR REPLACE INTO help_topics (codigo, titulo, conteudo, ordem)
            VALUES (%s, %s, %s, %s)
            ''',
            (codigo, titulo, conteudo, ordem)
        )

# Textos de ajuda
AJUDA_GERAL = """
*🤖 Bem-vindo à Ajuda do Dcyber Bot!*

*Comandos Disponíveis:*
/start - Inicia o bot
/ajuda - Mostra esta mensagem
/assinaturas - Menu de assinaturas
/casos - Menu de casos
/contatos - Menu de contatos
/lembretes - Menu de lembretes
/stats - Estatísticas

*Dicas Rápidas:*
• Use o menu principal para navegar
• Clique nos botões 🔙 para voltar
• Use /cancel para cancelar operações

*Precisa de ajuda específica%s*
Selecione um tópico abaixo 👇
"""

AJUDA_ASSINATURAS = """
*📑 Ajuda - Assinaturas*

*Como solicitar uma assinatura:*
1. Acesse o menu Assinaturas
2. Clique em "Solicitar Assinatura"
3. Digite o texto do documento
4. Aguarde a aprovação do DPC

*Dicas:*
• Você pode enviar vários documentos
• Separe cada documento em uma linha
• Aguarde a notificação de aprovação

*Comandos úteis:*
/assinaturas - Abre o menu
/consultar - Consulta suas assinaturas
"""

AJUDA_CASOS = """
*📁 Ajuda - Casos*

*Como criar um novo caso:*
1. Acesse o menu Casos
2. Clique em "Novo Caso"
3. Siga as instruções na tela
4. Adicione responsáveis

*Dicas:*
• Mantenha o status atualizado
• Adicione observações relevantes
• Você pode editar casos existentes

*Comandos úteis:*
/casos - Abre o menu
/novocaso - Cria novo caso
/meuscasos - Lista seus casos
"""

AJUDA_CONTATOS = """
*📇 Ajuda - Contatos*

*Como adicionar contatos:*
1. Acesse menu Contatos
2. Clique em "Novo Contato"
3. Digite as informações
4. Confirme o cadastro

*Formato do contato:*
Nome
Telefone/Email
Observações (opcional)

*Comandos úteis:*
/contatos - Abre o menu
/novocontato - Adiciona contato
/buscar - Pesquisa contatos
"""

AJUDA_LEMBRETES = """
*⏰ Ajuda - Lembretes*

*Como criar lembretes:*
1. Acesse menu Lembretes
2. Clique em "Novo Lembrete"
3. Digite título e data/hora
4. Selecione destinatários

*Dicas:*
• Use formato DD/MM/YYYY
• Horário em 24h (HH:MM)
• Você receberá notificações

*Comandos úteis:*
/lembretes - Abre o menu
/novolembrete - Cria lembrete
/meuslembretes - Lista lembretes
"""