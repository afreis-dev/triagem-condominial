# Condo Incident Compass

Act as a Frontend Engineer using React + Tailwind CSS.

Build ONLY the Syndic Queue Dashboard (Mobile-first 390px, responsive for desktop).

LAYOUT & COMPONENTS NEEDED:

1. Top Bar: 3 Tabs ("Nova", "Em andamento", "Concluída"). Default: "Nova".

2. Priority Summary Banner: Badges showing counts: Urgente (Red #B42318), Alta (Orange), Normal (Blue), Baixa (Gray). Always show full text + color.

3. Filter Bar: Dropdowns/Chips to filter by Condominium and Priority with a "Limpar Filtros" button.

4. Button "Colar Mensagem": Opens a Modal to select Condo and paste a WhatsApp text.

5. Card List (CartaoOcorrencia): Cards with max 4 lines (Priority Badge, Condo Name, Title, Origin, Elapsed Time, Short Reason). Clicking a card navigates to /ocorrencia/1.

6. Footer Pagination: Buttons [Anterior] [1] [2] [3] [Próximo] limiting view to 10 cards per page.

7. Empty State: Displays "Nenhuma ocorrência nova" when list is empty.

Create realistic in-code mock data for 15 occurrences across 3 condos.

Do NOT build a landing page. Build a clean dashboard route at /fila.

This project was built with [Lovable](https://lovable.dev).

## Build with Lovable

Continue developing this project in the [Lovable editor](https://lovable.dev/projects/f12b930b-f6bb-4070-892b-7988cf76cf42).

- **Ship faster**: describe what you want to build and Lovable handles the code.
- **Stay in sync**: every change made in Lovable is committed straight to this repository.
- **Full ownership**: this code is yours. Push to `main` on GitHub and your changes sync back into Lovable, ready for your next prompt.

## Development

Prefer working locally? You need Node.js and npm — [install with nvm](https://github.com/nvm-sh/nvm#installing-and-updating).

```sh
git clone <this-repository-url>
cd <repository-name>
npm i
npm run dev
```
