from decimal import Decimal

from app.features.expenses.algorithms.dinic import Dinic, Edge

# We convert Decimal amounts to integer cents for the flow network,
# then convert back to Decimal at the end.
_CENT = Decimal("0.01")


def simplify_debts(
    balances: list[tuple[str, Decimal]],
) -> list[tuple[str, str, Decimal]]:
    """Return the minimal set of payments that settle all debts.

    Parameters
    ----------
    balances:
        ``(username, net_balance)`` pairs.
        Positive means the user is *owed* money (creditor).
        Negative means the user *owes* money (debtor).

    Returns
    -------
    list of ``(from_user, to_user, amount)`` triples — each a payment
    that should be made.  Only non-zero amounts are included.
    """
    debtors: list[tuple[str, int]] = []  # (username, amount_in_cents)
    creditors: list[tuple[str, int]] = []

    for username, bal in balances:
        cents = int(bal / _CENT)
        if cents < 0:
            debtors.append((username, -cents))
        elif cents > 0:
            creditors.append((username, cents))

    if not debtors or not creditors:
        return []

    # Node layout: 0 = source, 1..D = debtors, D+1..D+C = creditors, last = sink
    nd = len(debtors)
    nc = len(creditors)
    source = 0
    sink = nd + nc + 1
    n_nodes = sink + 1

    dinic = Dinic(n_nodes)

    # source → each debtor
    for i, (_, amt) in enumerate(debtors):
        dinic.add_edge(source, 1 + i, amt)

    # each creditor → sink
    for j, (_, amt) in enumerate(creditors):
        dinic.add_edge(nd + 1 + j, sink, amt)

    # each debtor → each creditor (capacity = min of both, but INF works too)
    debtor_creditor_edges: list[tuple[int, int, Edge]] = []
    for i in range(nd):
        for j in range(nc):
            edge = dinic.add_edge(
                1 + i, nd + 1 + j, min(debtors[i][1], creditors[j][1])
            )
            debtor_creditor_edges.append((i, j, edge))

    dinic.max_flow(source, sink)

    # Read results
    payments: list[tuple[str, str, Decimal]] = []
    for i, j, edge in debtor_creditor_edges:
        if edge.flow > 0:
            payments.append(
                (
                    debtors[i][0],
                    creditors[j][0],
                    Decimal(edge.flow) * _CENT,
                )
            )

    return payments
