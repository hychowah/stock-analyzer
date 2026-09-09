"""Alternative-history pages and JSON. Does not call Live NAV."""

from __future__ import annotations

from html import escape as html_escape
from urllib.parse import quote

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response

from packages.catalog_api.client import CatalogApi

from apps.analysis_web.deps import get_api, get_history_service
from apps.analysis_web.services.alt_history import (
    NotFoundError,
    ReplayError,
    buy_universe,
    drop_hyp_fill,
    resolve_buy,
    resolve_sell,
    state_on,
    utc_today as _utc_today,
    with_hyp_fill,
)
from apps.analysis_web.services.alt_history_store import (
    copy_history,
    create_from_ib,
    delete_history,
    get_history,
    list_histories,
    save,
    update_history,
)
from apps.analysis_web.services.alt_history_view import (
    close_getter,
    earliest_stock_date,
    editor_page,
    history_document,
    holdings_on,
    list_payload,
    path_on,
    sold_later_listings,
)
from apps.analysis_web.services.portfolio import load_ib_book
from apps.analysis_web.services.price_history import HistoryService
from apps.analysis_web.templating import render_fragment, render_page

router = APIRouter(tags=["histories"])


def _opt_float(raw: str | None) -> float | None:
    s = str(raw or "").strip()
    if not s:
        return None
    try:
        n = float(s)
    except ValueError:
        return None
    if n != n or n in (float("inf"), float("-inf")):
        return None
    return n


def _redirect(hid: int, flash: str | None = None, date: str | None = None) -> RedirectResponse:
    url = f"/portfolio/histories/{int(hid)}"
    q: list[str] = []
    if date:
        q.append("date=" + quote(date))
    if flash:
        q.append("flash=" + quote(flash))
    if q:
        url += "?" + "&".join(q)
    return RedirectResponse(url, status_code=303)


def _empty_list_payload() -> dict:
    return {"cards": [], "overlay_svg": None, "max_date": "", "base_currency": ""}


@router.get("/portfolio/histories", response_class=HTMLResponse)
def page_histories(
    request: Request,
    svc: HistoryService = Depends(get_history_service),
) -> HTMLResponse:
    try:
        rows = list_histories()
    except ReplayError as e:
        return render_page(
            request,
            "histories.html",
            error=e.message,
            payload=_empty_list_payload(),
        )
    payload = list_payload(rows, svc)
    return render_page(request, "histories.html", payload=payload, error=None)


@router.get("/portfolio/histories/new", response_class=HTMLResponse)
def page_history_new(
    request: Request,
    error: str = "",
    history_name: str = "",
) -> HTMLResponse:
    ib_book, err = load_ib_book()
    if ib_book is None:
        return render_page(
            request,
            "history_new.html",
            error=err or "Import an IB activity statement first.",
            history_name=history_name,
        )
    return render_page(
        request,
        "history_new.html",
        error=error,
        history_name=history_name,
        trade_count=len(
            [t for t in ib_book.trades if (t.asset_category or "Stocks").lower() == "stocks"]
        ),
        min_date=earliest_stock_date(ib_book) or "",
    )


@router.post("/portfolio/histories/new")
def post_history_new(
    request: Request,
    name: str = Form(""),
):
    ib_book, err = load_ib_book()
    if ib_book is None:
        return page_history_new(
            request, error=err or "Import an IB activity statement first.", history_name=name
        )
    try:
        hist = create_from_ib(ib_book, name=name)
    except ReplayError as e:
        return page_history_new(request, error=e.message, history_name=name)
    return _redirect(int(hist.id or 0))


@router.get("/portfolio/histories/{history_id}", response_class=HTMLResponse)
def page_history_detail(
    request: Request,
    history_id: int,
    date: str = "",
    api: CatalogApi = Depends(get_api),
) -> HTMLResponse:
    try:
        hist = get_history(history_id)
    except NotFoundError:
        return render_page(
            request,
            "error.html",
            status_code=404,
            title="What-if",
            message="History not found",
        )
    except ReplayError as e:
        return render_page(
            request,
            "error.html",
            status_code=400,
            title="What-if",
            message=e.message,
        )
    payload = editor_page(
        hist,
        view_date=date or None,
        universe=buy_universe(api),
    )
    return render_page(request, "history_detail.html", payload=payload)


@router.post("/portfolio/histories/{history_id}")
def post_history_meta(
    history_id: int,
    name: str = Form(""),
    notes: str = Form(""),
):
    try:
        hist = update_history(history_id, name=name, notes=notes)
    except NotFoundError:
        return RedirectResponse("/portfolio/histories", status_code=303)
    return _redirect(int(hist.id or 0))


@router.post("/portfolio/histories/{history_id}/decisions")
def post_decision(
    request: Request,
    history_id: int,
    side: str = Form(""),
    ticker: str = Form(""),
    listing: str = Form(""),
    as_of: str = Form(""),
    quantity: str = Form(""),
    notional: str = Form(""),
    override_price: str = Form(""),
    api: CatalogApi = Depends(get_api),
    svc: HistoryService = Depends(get_history_service),
):
    try:
        hist = get_history(history_id)
    except NotFoundError:
        return render_page(
            request,
            "error.html",
            status_code=404,
            title="What-if",
            message="History not found",
        )
    except ReplayError as e:
        return render_page(
            request,
            "error.html",
            status_code=400,
            title="What-if",
            message=e.message,
        )
    get_close = close_getter(svc, start=hist.fork_date)
    day = (as_of or _utc_today()).strip()[:10]
    try:
        if day < hist.fork_date:
            raise ReplayError("before_fork", "Date is before the copied ledger starts.")
        kind = (side or "").strip().lower()
        qty = _opt_float(quantity)
        notion = _opt_float(notional)
        override = _opt_float(override_price)
        if kind == "buy":
            fill = resolve_buy(
                api,
                hist,
                ticker=ticker,
                as_of=day,
                quantity=qty,
                notional=notion,
                override_price=override,
                get_close=get_close,
            )
        elif kind == "sell":
            if not (listing or "").strip():
                raise ReplayError(
                    "empty_listing",
                    "Sell a listing from the holdings table.",
                )
            held = state_on(hist, day)
            fill = resolve_sell(
                held,
                hist,
                listing=listing,
                as_of=day,
                quantity=qty,
                notional=notion,
                override_price=override,
                get_close=get_close,
            )
        else:
            raise ReplayError("bad_side", "Choose buy or sell")
        save(with_hyp_fill(hist, fill))
    except ReplayError as e:
        payload = editor_page(
            hist,
            view_date=day,
            universe=buy_universe(api),
            error=e.message,
        )
        return render_page(
            request, "history_detail.html", status_code=400, payload=payload
        )
    return _redirect(history_id, date=day)


@router.post("/portfolio/histories/{history_id}/decisions/{decision_id}/delete")
def post_delete_decision(
    request: Request,
    history_id: int,
    decision_id: int,
    api: CatalogApi = Depends(get_api),
):
    try:
        hist = get_history(history_id)
    except NotFoundError:
        return RedirectResponse("/portfolio/histories", status_code=303)
    except ReplayError as e:
        return render_page(
            request,
            "error.html",
            status_code=400,
            title="What-if",
            message=e.message,
        )
    try:
        save(drop_hyp_fill(hist, decision_id))
    except ReplayError as e:
        payload = editor_page(
            hist,
            universe=buy_universe(api),
            error=e.message,
        )
        return render_page(
            request, "history_detail.html", status_code=400, payload=payload
        )
    return _redirect(history_id)


@router.post("/portfolio/histories/{history_id}/copy")
def post_copy(history_id: int) -> RedirectResponse:
    try:
        copied = copy_history(history_id)
    except NotFoundError:
        return RedirectResponse("/portfolio/histories", status_code=303)
    return _redirect(int(copied.id or 0))


@router.post("/portfolio/histories/{history_id}/delete")
def post_delete_history(history_id: int) -> RedirectResponse:
    try:
        delete_history(history_id)
    except NotFoundError:
        pass
    return RedirectResponse("/portfolio/histories", status_code=303)


@router.get("/api/portfolio/histories")
def api_histories(
    svc: HistoryService = Depends(get_history_service),
):
    try:
        rows = list_histories()
    except ReplayError as e:
        return JSONResponse({"error": e.code, "message": e.message, "histories": []}, status_code=400)
    payload = list_payload(rows, svc)
    return {
        "error": None,
        "until": payload["until"],
        "base_currency": payload["base_currency"],
        "histories": [
            {
                "id": c["id"],
                "name": c["name"],
                "fork_date": c["fork_date"],
                "n_decisions": c["n_decisions"],
                "actual_nav": c["actual_nav"],
                "alt_nav": c["alt_nav"],
                "delta": c["delta"],
                "path": c["path"],
            }
            for c in payload["cards"]
        ],
    }


@router.get("/api/portfolio/histories/{history_id}")
def api_history(history_id: int):
    try:
        hist = get_history(history_id)
    except NotFoundError:
        return JSONResponse({"error": "not_found"}, status_code=404)
    except ReplayError as e:
        return JSONResponse({"error": e.code, "message": e.message}, status_code=400)
    return history_document(hist).as_json()


@router.get("/api/portfolio/histories/{history_id}/holdings")
def api_history_holdings(
    history_id: int,
    date: str = Query(""),
    svc: HistoryService = Depends(get_history_service),
):
    try:
        hist = get_history(history_id)
    except NotFoundError:
        return JSONResponse({"error": "not_found"}, status_code=404)
    except ReplayError as e:
        return JSONResponse({"error": e.code, "message": e.message}, status_code=400)
    body = holdings_on(hist, svc, view_date=date or None).as_json()
    body["id"] = hist.id
    return body


@router.get(
    "/fragments/portfolio/histories/{history_id}/held",
    response_class=HTMLResponse,
)
def fragment_held_table(
    request: Request,
    history_id: int,
    date: str = Query(""),
    svc: HistoryService = Depends(get_history_service),
) -> HTMLResponse:
    try:
        hist = get_history(history_id)
    except NotFoundError:
        return HTMLResponse(
            '<p class="muted">History not found</p>', status_code=404
        )
    except ReplayError as e:
        return HTMLResponse(
            f'<p class="err" role="alert">{html_escape(e.message)}</p>',
            status_code=400,
        )
    view = holdings_on(hist, svc, view_date=date or None)
    return render_fragment(
        request,
        "partials/held_table.html",
        history_id=hist.id,
        view_date=view.view_date,
        held=view.held,
        cash=view.cash,
        base_currency=view.base_currency,
        sold_later=sold_later_listings(hist, view.view_date),
    )


@router.get("/api/portfolio/histories/{history_id}/path")
def api_history_path(
    history_id: int,
    svc: HistoryService = Depends(get_history_service),
):
    try:
        hist = get_history(history_id)
    except NotFoundError:
        return JSONResponse({"error": "not_found"}, status_code=404)
    except ReplayError as e:
        return JSONResponse({"error": e.code, "message": e.message}, status_code=400)
    body = path_on(hist, svc).as_json()
    body["id"] = hist.id
    return body


@router.get("/api/portfolio/histories/{history_id}/path.svg")
def api_history_path_svg(
    history_id: int,
    svc: HistoryService = Depends(get_history_service),
):
    try:
        hist = get_history(history_id)
    except NotFoundError:
        return JSONResponse({"error": "not_found"}, status_code=404)
    except ReplayError as e:
        return JSONResponse({"error": e.code, "message": e.message}, status_code=400)
    svg = path_on(hist, svc).svg or (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 160"></svg>'
    )
    return Response(content=svg, media_type="image/svg+xml")
