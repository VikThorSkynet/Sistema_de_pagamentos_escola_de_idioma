# Sistema_de_pagamentos_escola_de_idioma
# Sistema de Pagamentos - Relatório Financeiro

## Visão Geral

Este é um aplicativo de desktop desenvolvido em Python usando a biblioteca Tkinter (com ttk para widgets temáticos) para gerenciar pagamentos de mensalidades de alunos e acompanhar devedores. Ele utiliza um banco de dados PostgreSQL para armazenar e recuperar informações. O aplicativo permite adicionar, visualizar, atualizar e remover registros de alunos/pagamentos, gerenciar o status de pagamento mensal e exportar relatórios para arquivos Excel.

## Funcionalidades Principais

### Aba "Pagamentos"

*   **Visualização de Pagamentos:** Exibe uma tabela com os dados financeiros dos alunos, incluindo:
    *   ID do Aluno
    *   Dia de Vencimento/Pagamento
    *   Nome do Aluno
    *   Curso
    *   Valor do Desconto (se aplicável)
    *   Valores de pagamento base para cada mês (Janeiro a Dezembro).
*   **Status Visual:** Indica o status de cada pagamento mensal diretamente na tabela:
    *   **✅ (Pago):** Marca um pagamento que foi confirmado como recebido (registrado na tabela `student_debtors` como 'Pago').
    *   **❌ (Devedor):** Marca um pagamento que está 'Pendente' ou 'Em Negociação' na tabela `student_debtors`.
    *   *(Sem marca):* O valor base existe, mas o status ainda não foi definido, ou o valor é zero.
*   **Gerenciamento de Alunos:**
    *   **Adicionar:** Permite adicionar novos alunos com seus dados de pagamento base.
    *   **Atualizar:** Modifica os dados de um aluno existente (incluindo valores mensais). A atualização também reflete o nome/curso/valor na tabela de devedores, se aplicável, mas **não altera o status** ('Pendente', 'Pago', etc.) que é gerenciado separadamente.
    *   **Remover:** Exclui permanentemente um aluno e **todos os seus registros associados** (pagamentos e débitos, devido à configuração `ON DELETE CASCADE` no banco de dados).
*   **Busca:** Filtra a lista de alunos por ID ou Nome.
*   **Gerenciamento de Status Mensal:**
    *   Ao selecionar um aluno, botões de status ("Status JAN", "Status FEV", etc.) são habilitados.
    *   Clicar em um botão permite marcar o pagamento daquele mês como "Pago" ou "Devedor".
    *   Essa ação cria ou atualiza um registro correspondente na tabela `student_debtors`.
    *   Se o valor base do mês for zero, o status não pode ser aplicado.
*   **Próximo ID:** Calcula e sugere o próximo ID numérico disponível (na faixa 1001-9999) para adicionar um novo aluno.
*   **Exportar para Excel:** Exporta a visualização *atual* da tabela de pagamentos (incluindo as marcas de status ✅/❌) para um arquivo `.xlsx`.
*   **Dados de Exemplo:** Se o banco de dados estiver vazio, oferece a opção de carregar dados de exemplo para demonstração.

### Aba "Devedores"

*   **Visualização de Devedores:** Exibe uma tabela **filtrada** mostrando apenas os registros da tabela `student_debtors` com status 'Pendente' ou 'Em Negociação'. Inclui:
    *   ID do Aluno
    *   Nome do Aluno
    *   Curso
    *   Mês em Dívida
    *   Valor Devido
    *   Status Atual ('Pendente' ou 'Em Negociação')
    *   Comentário Associado
*   **Codificação por Cores:** As linhas são coloridas com base no status para fácil identificação:
    *   Vermelho claro: Pendente
    *   Amarelo claro: Em Negociação
*   **Busca:** Filtra a lista de devedores por ID ou Nome do Aluno.
*   **Gerenciamento de Status e Comentários:**
    *   Ao selecionar um registro de devedor, os campos abaixo da tabela são preenchidos.
    *   Permite **atualizar o Status** (para 'Pendente', 'Em Negociação' ou 'Pago'), **editar o Comentário** e **corrigir o Valor** devido diretamente nesta aba.
    *   Atualizar o status para 'Pago' aqui efetivamente remove o aluno da lista de devedores visíveis *nesta aba* (mas o registro ainda existe no banco com status 'Pago') e atualiza a marca na aba "Pagamentos".
*   **Remover da Lista:** Remove o registro de débito *específico* (para aquele aluno e mês) da tabela `student_debtors`. Isso **não** altera o valor base na aba "Pagamentos", apenas remove a marca ❌ e a entrada da lista de devedores. Útil se um débito foi registrado por engano ou resolvido de outra forma.
*   **Exportar Devedores para Excel:** Exporta a visualização *atual* da tabela de devedores (apenas os pendentes/em negociação visíveis) para um arquivo `.xlsx`. Os valores monetários são exportados como texto formatado (com vírgula).

## Pré-requisitos

Antes de executar o aplicativo, você precisará ter:

1.  **Python:** Versão 3.6 ou superior.
2.  **PostgreSQL:** Um servidor PostgreSQL instalado e em execução.
    *   Você precisará de um banco de dados e um usuário com permissões para criar tabelas e realizar operações CRUD (Criar, Ler, Atualizar, Deletar) nesse banco.
    *   O script assume um banco chamado `postgres` e um usuário `postgres` com senha `123`. **É ALTAMENTE RECOMENDADO alterar essas credenciais!**
3.  **Bibliotecas Python:**
    *   `psycopg2` (ou `psycopg2-binary` para facilitar a instalação): Para interagir com o PostgreSQL.
    *   `pandas`: Para a funcionalidade de exportação para Excel.
    *   `openpyxl`: Necessário pelo `pandas` para trabalhar com arquivos `.xlsx`.

## Instalação e Configuração

1.  **Clone ou Baixe o Repositório:**
    ```bash
    git clone <url-do-repositorio> # Ou baixe o arquivo ZIP
    cd <diretorio-do-projeto>
    ```

2.  **Crie um Ambiente Virtual (Recomendado):**
    ```bash
    python -m venv venv
    # No Windows
    venv\Scripts\activate
    # No macOS/Linux
    source venv/bin/activate
    ```

3.  **Instale as Dependências:**
    ```bash
    pip install psycopg2-binary pandas openpyxl
    ```
    *(Se você preferir compilar `psycopg2`, use `pip install psycopg2 pandas openpyxl` e certifique-se de ter as ferramentas de compilação e bibliotecas de desenvolvimento do PostgreSQL instaladas).*

4.  **Configure o Banco de Dados PostgreSQL:**
    *   Certifique-se de que o serviço PostgreSQL esteja em execução.
    *   Verifique se o banco de dados (`postgres` por padrão no script) e o usuário (`postgres` com senha `123` por padrão) existem e se o usuário tem as permissões necessárias. Se não, crie-os usando ferramentas como `psql` ou pgAdmin.

5.  **⚠️ IMPORTANTE: Configure a Conexão do Banco de Dados no Script:**
    *   Abra o arquivo `teste_relafinFinal.py` em um editor de texto.
    *   Localize a função `connect_to_db(self)`:
        ```python
        def connect_to_db(self):
            try:
                # VERIFIQUE ESTAS CREDENCIAIS
                self.conn = psycopg2.connect(
                    host="localhost",       # Mude se seu DB estiver em outro host
                    database="postgres",    # Mude se usar outro nome de banco
                    user="",                # Mude para seu usuário do DB
                    password="",            # MUDE PARA SUA SENHA DO DB!
                    client_encoding="utf8"
                )
                self.cursor = self.conn.cursor()
                return self.conn, self.cursor
            except Exception as e:
                messagebox.showerror("Database Error", f"Could not connect: {str(e)}")
                self.conn, self.cursor = None, None
                return None, None
        ```
    *   **Altere os valores de `host`, `database`, `user` e `password`** para corresponderem à sua configuração do PostgreSQL.
    *   **NÃO** comite o arquivo com senhas reais para repositórios públicos. Considere usar variáveis de ambiente ou arquivos de configuração para gerenciar credenciais em um ambiente de produção.

## Executando o Aplicativo

Com o ambiente virtual ativado e as dependências instaladas, execute o script Python:

```bash
python teste_relafinFinal.py
Use code with caution.
Markdown
O aplicativo deve iniciar. Na primeira execução, ele tentará criar as tabelas student_payments e student_debtors no banco de dados configurado, caso ainda não existam. Se o banco estiver vazio, ele perguntará se você deseja carregar dados de exemplo.
Guia de Uso Básico
Navegação: Use as abas "Pagamentos" e "Devedores" para alternar entre as visualizações.
Adicionar Aluno:
Vá para a aba "Pagamentos".
Clique em "Próximo ID" ou digite um ID único (1001-9999).
Preencha os campos "Dia Pgto", "Nome", "Curso", "Desconto" (opcional, use formato XX,XX), e os valores base mensais (formato XX,XX).
Clique em "Adicionar".
Atualizar Aluno:
Selecione o aluno na tabela da aba "Pagamentos". Os campos do formulário serão preenchidos.
Modifique os campos desejados.
Clique em "Atualizar".
Remover Aluno:
Selecione o aluno na tabela da aba "Pagamentos" OU digite o ID no campo "ID".
Clique em "Remover".
Confirme a ação (lembre-se que isso é permanente e remove todos os dados).
Marcar Status de Pagamento:
Selecione o aluno na aba "Pagamentos".
Clique no botão "Status [MÊS]" correspondente ao mês que deseja marcar.
Escolha "Pago" ou "Devedor" na caixa de diálogo.
Isso atualizará a marca (✅/❌) na aba "Pagamentos" e o registro na tabela/aba "Devedores".
Gerenciar Devedores:
Vá para a aba "Devedores". A lista mostra apenas pendências.
Selecione um registro.
Use os campos abaixo para mudar o Status, adicionar/editar um Comentário ou corrigir o Valor. Clique em "Atualizar Status/Comentário".
Para remover um registro de débito específico (marcar como resolvido sem ser 'Pago' formalmente ou corrigir um erro), selecione-o e clique em "Remover da Lista".
Buscar: Digite parte do nome ou o ID completo nos campos de busca apropriados em cada aba e clique em "Buscar". Clique em "Mostrar Todos" para limpar a busca.
Exportar: Clique nos botões "Exportar Excel" (aba Pagamentos) ou "Exportar Devedores Excel" (aba Devedores) para salvar os dados da tabela atual em um arquivo .xlsx.
Esquema do Banco de Dados (Simplificado)
student_payments:
id (INTEGER, Chave Primária): ID único do aluno.
payment_day (INTEGER): Dia preferencial de pagamento.
student_name (VARCHAR): Nome do aluno.
course (VARCHAR): Curso do aluno.
discount (DECIMAL): Valor do desconto aplicado à mensalidade base.
jan, feb, ..., dec (DECIMAL): Valor base da mensalidade para cada mês.
student_debtors:
id (INTEGER, Chave Estrangeira -> student_payments.id ON DELETE CASCADE): ID do aluno.
student_name (VARCHAR): Nome do aluno (redundante, mas usado para exibição).
course (VARCHAR): Curso (redundante).
month (VARCHAR): Nome completo do mês (ex: "Janeiro", "Fevereiro").
amount (DECIMAL): Valor devido para aquele mês (pode ser diferente do valor base se houver negociação ou correção).
status (VARCHAR): Status do débito ('Pendente', 'Em Negociação', 'Pago').
comment (TEXT): Comentário opcional sobre o débito.
(Chave Primária Composta: id, month)
Notas Importantes e Caveats
Credenciais Hardcoded: As credenciais do banco de dados estão diretamente no código (connect_to_db). Isso não é seguro para ambientes de produção. Use métodos mais seguros como variáveis de ambiente, arquivos de configuração seguros ou gerenciadores de segredos.
Dependência de Locale: A formatação de moeda (format_currency, parse_currency) tenta usar o locale pt_BR. Se esse locale não estiver configurado corretamente no sistema operacional, a formatação pode falhar ou usar o padrão do sistema.
Cascade Delete: A remoção de um aluno na aba "Pagamentos" excluirá todos os registros associados na tabela student_debtors devido à restrição FOREIGN KEY ... ON DELETE CASCADE. Tenha cuidado ao remover alunos.
Interface do Usuário: A interface é construída com Tkinter e pode ter a aparência padrão do sistema operacional ou a aparência do tema ttk ('clam' é tentado por padrão). A responsividade é básica; em telas muito pequenas ou muito grandes, o layout pode não ser ideal.
Validação: Existe validação básica para os campos do formulário (ID, dia, valores numéricos), mas entradas inesperadas ainda podem causar erros.
Contribuições
Contribuições são bem-vindas! Se encontrar bugs ou tiver sugestões de melhorias, sinta-se à vontade para abrir uma Issue ou enviar um Pull Request.
