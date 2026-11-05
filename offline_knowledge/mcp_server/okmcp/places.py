"""The find_place MCP tool: Offline Knowledge's own place search."""


def format_hits(query, hits):
    if not hits:
        return (
            f'No place found for "{query}". The search only knows what has been indexed; '
            "see the place_search option of the app."
        )
    lines = [f'Places for "{query}":']
    for hit in hits:
        where = ", ".join(x for x in (hit.get("near"), hit.get("country")) if x)
        where = f", {where}" if where else ""
        lines.append(f"- {hit['name']} ({hit['kind']}{where}): {hit['lat']:.5f}, {hit['lon']:.5f}")
    return "\n".join(lines)
