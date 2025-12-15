# Cegonha Lanches - Frontend (Cliente & Admin)

Interface web responsiva para o sistema de delivery, desenvolvida com tecnologias nativas (Vanilla JS), sem necessidade de frameworks pesados como React ou Vue. Inclui tanto a área do cliente quanto o painel administrativo.

## Tecnologias
- HTML5 Semântico
- CSS3 Moderno (Flexbox, Grid, Variáveis CSS)
- JavaScript (ES6 Modules, Fetch API, Async/Await)
- FontAwesome (Ícones)

## Funcionalidades Principais

### Área do Cliente
- **Cardápio Digital:** Renderização dinâmica de lanches e combos vindos da API.
- **Carrinho Inteligente:** Gestão de itens, cálculo de total e persistência local.
- **Personalização:** Modal para escolha de carnes, adicionais e bebidas.
- **Autenticação:** Login e Cadastro com JWT (armazenado no LocalStorage).
- **Perfil:** Gestão de dados pessoais e múltiplos endereços de entrega.
- **Meus Pedidos:** Histórico com atualização de status em tempo real (Polling).
- **Chat:** Widget flutuante para conversar com o restaurante.

### Painel Administrativo (/admin.html)
- **Gestão de Pedidos:** Visualização estilo Kanban (Recebido -> Preparo -> Entrega).
- **Gestão de Cardápio:** Criar, editar, excluir e pausar produtos.
- **Chat Admin:** Interface de atendimento para responder clientes.
- **Segurança:** Proteção de rotas e confirmação de ações destrutivas.

## Como Rodar
Como é um projeto estático, você precisa apenas de um servidor HTTP simples para evitar bloqueios de CORS do navegador.

1. Abra o terminal na pasta deste projeto.
2. Execute o servidor simples do Python:
   python -m http.server 8000
3. Acesse no navegador:
   - Cliente: http://localhost:8000
   - Admin: http://localhost:8000/admin.html
