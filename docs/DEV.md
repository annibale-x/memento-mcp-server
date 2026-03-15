
# MCP CLI COMMANDS

python -m context_keeper 
python -m context_keeper --help
python -m context_keeper --health

# TOOLS

Lista dei 19 Tool Esposti (Extended + Advanced):

### Core Tools (10):
1. **`help_memory_tools_usage`** - Get guidance on using persistent memory tools and distinguishing from session memory
2. **`store_persistent_memory`** - Store a new persistent memory with context and metadata
3. **`get_persistent_memory`** - Retrieve a specific persistent memory by ID
4. **`search_persistent_memories`** - Search persistent memories using natural language queries
5. **`update_persistent_memory`** - Update an existing persistent memory
6. **`delete_persistent_memory`** - Delete a persistent memory by ID
7. **`create_persistent_relationship`** - Create relationships between persistent memories
8. **`get_related_persistent_memories`** - Get persistent memories related to a specific memory
9. **`recall_persistent_memories`** - Primary tool for finding past persistent memories (fuzzy matching)
10. **`get_persistent_recent_activity`** - Get recent persistent memory activity

### Extended Extra Tools (3):
11. **`get_persistent_memory_statistics`** - Get statistics about stored persistent memories
12. **`search_persistent_relationships_by_context`** - Search persistent relationships by context
13. **`persistent_contextual_search`** - Context-aware persistent memory search

### Advanced Tools (7):
14. **`analyze_persistent_memory_graph`** - Analyze the persistent memory relationship graph
15. **`find_persistent_patterns`** - Find patterns in persistent memories
16. **`suggest_persistent_relationships`** - Suggest potential relationships between persistent memories
17. **`get_persistent_memory_clusters`** - Get clusters of related persistent memories
18. **`get_persistent_central_memories`** - Find central/important persistent memories in the graph
19. **`find_path_between_persistent_memories`** - Find connection paths between persistent memories
20. **`get_persistent_memory_network`** - Get the network structure of persistent memories

**Totale: 20 tool**

Se vuoi solo i 13 tool del profilo "extended" (senza advanced), devi impostare `CONTEXT_ENABLE_ADVANCED_TOOLS=false` nella configurazione Zed.

## IMPORTANTE: Convenzione di denominazione `_persistent`

Tutti i tool di mcp-context-keeper utilizzano il suffisso `_persistent` per distinguerli dai tool di session memory di Serena Context Server:

- **Tool persistenti** (`_persistent` suffix): Memoria a lungo termine, cross-session, globale
- **Tool di sessione** (senza suffix): Memoria temporanea, project-specific, session-only

**Esempio di confusione da evitare:**
- ❌ `store_memory` (Serena) per soluzioni a lungo termine
- ✅ `store_persistent_memory` (mcp-context-keeper) per soluzioni a lungo termine

Usa `help_memory_tools_usage` per una guida completa sulla distinzione.


# CROSS COMPILATION

### Opzione 1: Usare `cross` (la più comoda per casi complessi)
Se il tuo progetto ha dipendenze C (come spesso succede), la cross-compilation manuale può diventare un incubo. Esiste **`cross`**, un wrapper che usa Docker per gestire tutto automaticamente:

```bash
# Installa cross
cargo install cross

# Compila per Windows (senza impazzire)
cross build --target x86_64-pc-windows-gnu --release
```
`cross` si occupa di tutto: toolchain, linker, librerie di sistema .

## Casi particolari da tenere d'occhio

| Scenario | Problema | Soluzione |
|----------|----------|-----------|
| **Dipendenze C** (es. `ring`, `openssl-sys`) | La compilazione incrociata fallisce perché cerca librerie C del sistema target | Usa `cross` con Docker, o installa manualmente le librerie di cross-compilation  |
| **Glibc vs musl** | Binario Linux compilato su Ubuntu potrebbe non funzionare su CentOS vecchio (versione glibc diversa) | Compila per `x86_64-unknown-linux-musl` per avere binari statici che girano **su qualsiasi Linux**  |
| **Windows MSVC vs GNU** | `x86_64-pc-windows-msvc` (Micosoft) dà eseguibili più "nativi", ma richiede Visual Studio | Per semplicità, usa `x86_64-pc-windows-gnu` (MinGW)  |
| **macOS** | Compilare per macOS da Linux è **estremamente difficile** per via delle licenze Apple | Compila nativamente su Mac o usa CI su GitHub Actions con runner macOS  |

## Opzione 2:

Considerando che stai sviluppando un MCP server in Rust e vuoi distribuirlo su più piattaforme, ti consiglio:

1. **In fase di sviluppo**: compila nativamente sul sistema che stai usando
2. **Per le release**: usa GitHub Actions con una matrice di build che compila automaticamente per Windows, Linux e macOS 
3. **Per Linux**: considera di usare il target `musl` per avere un singolo eseguibile statico che funziona su tutte le distro

Esempio di matrice GitHub Actions:
```yaml
strategy:
  matrix:
    os: [ubuntu-latest, windows-latest, macos-latest]
    target: [x86_64-unknown-linux-gnu, x86_64-pc-windows-gnu, x86_64-apple-darwin]
```
