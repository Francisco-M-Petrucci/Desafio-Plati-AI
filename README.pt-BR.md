# ChefCompanion

O ChefCompanion é um aplicativo web conversacional focado em privacidade local (local-first) que sugere receitas hiperpersonalizadas aos usuários com base em seus eletrodomésticos, ingredientes disponíveis, restrições alimentares e preferências sazonais.

Este projeto foi desenvolvido para demonstrar um assistente de IA capaz de extração de memória de longo prazo e Geração Aumentada de Recuperação (RAG) para o desafio Plati AI.

## Arquitetura

O ChefCompanion combina três camadas de contexto para impulsionar a personalização:

1. **Contexto de Curto Prazo**: Tags de preferências temporárias ("Deseja" e "Não Deseja") combinadas com um histórico altamente compactado e simplificado das ações recentes do agente. Para evitar o inchaço do contexto, apenas a mensagem mais recente do usuário é passada para o prompt a cada turno, em vez de uma janela deslizante completa.
2. **Perfil do Usuário e Memória de Longo Prazo (SQLite)**: Inventário do usuário, eletrodomésticos disponíveis, restrições alimentares e fatos permanentes extraídos programaticamente ao longo das sessões.
3. **Base de Conhecimento (RAG)**: Uma coleção de busca vetorial carregada com receitas selecionadas que correspondem ao esquema do conjunto de dados Food.com Recipes.

### Fluxo de Trabalho do Agente (Orquestração com LangGraph)

```text
          INÍCIO
            |
            v
    [ Carregar Perfil ] ---- Busca estoque/eletrodomésticos/restrições/fatos do usuário no SQLite
            |
            v
  [ Extrair Preferências ] - Analisa a última mensagem para extrair fatos e a intenção do usuário
            |
            v
     [ Pré-Filtragem ] ----- Filtra receitas por eletrodomésticos/dieta antes de serem vistas pelo LLM
            |
            v
       [ LLM Agente ] ------ Formula o prompt e decide chamadas de ferramentas (RAG ou inventário)
            |
        +----+----+ (Roteamento condicional)
        v         v
  [Ferramentas] [Saída]
        |         |
        +---------+
            |
            v
           FIM
```

## Estratégia de Memória

O sistema conta com uma abordagem de memória em múltiplas camadas:
- **Pré-processamento de Extração de Fatos**: Antes da execução do LLM conversacional principal, um nó dedicado do LangGraph analisa a mensagem mais recente do usuário para extrair fatos permanentes (por exemplo, "Sou intolerante a lactose") e intenções temporárias (por exemplo, "Quero um jantar rápido"). Isso é analisado como JSON e persistido diretamente no banco de dados SQLite.
- **Isolamento de Contexto**: Cada usuário possui um perfil isolado no SQLite.
- **Segurança e Injeção de Prompt**: O prompt de extração de fatos envolve as mensagens do usuário em tags XML (`<user_message>`) e instrui explicitamente o extrator a ignorar instruções dentro das tags, evitando que injeções de prompt reescrevam fatos confidenciais no banco de dados.

## Estratégias de Minimização de Custo de Tokens

Para manter o desempenho e manter baixos os custos de tokens:
- **Pré-filtragem Determinística**: Antes de consultar o banco de dados vetorial ou enviar resultados para o LLM, o sistema filtra programaticamente as receitas que são incompatíveis com as restrições alimentares ou eletrodomésticos cadastrados do usuário. Isso evita o desperdício de tokens com dados irrelevantes.
- **Invocação Direcionada do RAG**: O LLM só pesquisa no banco de dados vetorial quando explicitamente solicitado ou quando uma intenção de recomendação é detectada, recorrendo ao conhecimento geral para dúvidas culinárias básicas.

## Tecnologias Utilizadas e Justificativa

- **Framework de Agentes**: `LangChain` e `LangGraph`. O LangGraph fornece controle ideal para orquestração de múltiplos turnos com estado. Ele permite um roteamento estrito entre extração de memória, execução de ferramentas e raciocínio do LLM com base em estados específicos da aplicação.
- **Mecanismo de LLM**: `Llama 3.3 70B Versatile` via **Groq**. 
  - *Por quê*: Este modelo é excelente em chamadas de ferramentas complexas e oferece velocidades de inferência excepcionais. Além disso, sua enorme janela de contexto de 128k acomoda facilmente o histórico de conversas extensas e os documentos recuperados por RAG sem risco de truncamento.
  - *Nota*: É altamente recomendável usar o modelo Groq Llama 3.3 70B Versatile. O uso de modelos alternativos ou mais fracos pode degradar significativamente a capacidade do agente de gerar chamadas de ferramentas válidas e seguir esquemas JSON estritos.
- **Banco de Dados (Memória de Longo Prazo)**: `SQLite`. Escolhido por sua natureza leve e sem necessidade de servidor (serverless). É ideal para uma prova de conceito local, permitindo uma configuração rápida e isolamento contínuo de contexto por usuário sem a necessidade de hospedagem de banco de dados externo.
- **Banco de Dados Vetorial (Base de Conhecimento)**: `Chroma`. Funciona de forma totalmente serverless e armazena embeddings localmente. Integra-se perfeitamente aos fluxos de trabalho em Python para buscas rápidas de similaridade sem dependências externas.
- **Backend**: `FastAPI` (Python). Execução assíncrona rápida e leve, com excelente documentação automática.

## Principais Desafios

Durante o desenvolvimento, o desafio mais significativo foi identificar a estratégia de orquestração e o modelo corretos. As iterações iniciais utilizaram um modelo menos capaz e uma estratégia de grafo complexa, o que resultou em erros contínuos com formatos de chamada de ferramentas e adesão ao esquema. Ao migrar para uma arquitetura LangGraph mais simples que conta com um nó extrator de intenções e atualizar para o Llama 3.3 70B da Groq, o desenvolvimento acelerou significativamente, resolvendo as inconsistências de chamada de ferramentas e melhorando a confiabilidade geral.

## Personalização Demonstrável (Casos de Teste)

Para verificar a hiperpersonalização, use as personas de teste pré-configuradas (senha: `password123`):

### Usuário A: Alice (Sem Glúten, Cozinha Rápida)
**Perfil:** Possui Airfryer, Sem Glúten, prefere refeições rápidas.
1. **Solicitação Direta:** Pergunte *"Estou com muita fome e só tenho cerca de 20 minutos para cozinhar algo. O que posso fazer com minhas asas de frango?"*
   **Resultado:** Recomenda uma receita rápida na airfryer com base nos ingredientes e fatos dela.
2. **Verificação de Segurança Alimentar:** Pergunte *"Posso fazer um prato de massa clássico?"*
   **Resultado:** O filtro estrito de pré-filtragem bloqueia todas as receitas com glúten. A IA apresentará apenas alternativas 100% livres de glúten.

### Usuário B: Bob (Vegetariano, Italiano Tradicional)
**Perfil:** Possui Forno, Vegetariano, não gosta de comida apimentada.
1. **Verificação de Memória:** Pergunte *"Quero fazer algo bem apimentado para o jantar, só por hoje à noite."*
   **Resultado:** O agente verifica os fatos de longo prazo dele e gentilmente o lembra de que ele geralmente não gosta de comida apimentada.
2. **RAG vs Conhecimento de Base:** Pergunte *"Tenho massa de pizza e mozarela fresca. Oriente-me a fazer uma pizza passo a passo."*
   **Resultado:** O agente responde a partir do conhecimento geral.
   Depois pergunte: *"Oriente-me a fazer uma pizza margherita passo a passo."*
   **Resultado:** O agente busca a receita específica de *Classic Italian Margherita Pizza* no banco de dados vetorial.

## Suíte de Avaliação

Para garantir programaticamente a segurança do aplicativo, a prevenção de alucinações e a intenção arquitetônica, uma suíte de testes robusta (`evals.py`) está incluída usando o `pytest`. 

A suíte compreende 11 casos de avaliação distintos que cobrem as três principais responsabilidades do agente:
1. **Pré-filtragem Determinística (5 casos):** Garante que usuários com restrições alimentares (por exemplo, Sem Glúten, Vegetariano) ou sem eletrodomésticos específicos (por exemplo, Forno) estritamente não recebam recomendações de receitas incompatíveis.
2. **Precisão na Extração de Fatos (3 casos):** Garante que o LLM analise corretamente as mensagens do usuário para memorizar fatos permanentemente (por exemplo, "treinando para uma maratona") e capturar temporariamente os desejos da sessão.
3. **Precisão na Seleção de Ferramentas (3 casos):** Garante que o LLM decida de forma confiável quando usar o Conhecimento de Base (chat geral) versus RAG (solicitações de receitas), gerenciando com sucesso o consumo de tokens e evitando pesquisas desnearias no banco de dados.

**Resultados:** `11/11 APROVADOS` (100% de Taxa de Sucesso). 

Para executar as avaliações localmente:
```bash
cd backend
pytest evals.py -v
```

## Roteiro de Implementações Futuras

- **Integração de OCR de Recibos:** Implementação de um recurso para upload de fotos de recibos de supermercado para analisar e atualizar automaticamente o inventário de cozinha do usuário usando um modelo de visão multimodal.
- **Banco de Dados de Receitas Ampliado:** Aumento significativo do tamanho do banco de dados vetorial Chroma para incluir uma variedade muito maior de receitas de diferentes culinárias e nichos alimentares.
- **Modo de Assistência de Cozinha:** Criação de um modo de interface dedicado viva-voz projetado para o momento ativo de cozinhar. Ele contará com botões grandes e acessíveis para navegação passo a passo, garantindo que usuários com as mãos sujas ou ocupadas não precisem digitar mensagens.

## Como Executar Localmente

### 1. Pré-requisitos
- Python 3.10+
- Node.js 18+

### 2. Configurar o Ambiente
Copie o arquivo `.env.example` para `.env` na raiz do projeto e preencha suas chaves:
```bash
cp .env.example .env
```
Certifique-se de preencher sua `GROQ_API_KEY` para o LLM principal.

### 3. Configuração Automatizada
A maneira mais fácil de instalar todas as dependências e popular o banco de dados é usando os scripts de configuração.

**Para Windows:**
```cmd
setup.bat
```

**Para Mac/Linux:**
```bash
chmod +x setup.sh start.sh
./setup.sh
```

### 4. Iniciar a Aplicação
**Para Windows:**
```cmd
start.bat
```

**Para Mac/Linux:**
```bash
./start.sh
```
A aplicação estará disponível em http://localhost:5173.
