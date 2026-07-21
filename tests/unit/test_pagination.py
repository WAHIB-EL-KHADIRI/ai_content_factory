"""Tests for pagination, search, and filtering utilities."""

from datetime import datetime, timedelta

import pytest
from sqlalchemy import Column, DateTime, Float, Integer, String, create_engine
from sqlalchemy.orm import Session, declarative_base

from backend.core.pagination import (
    PaginatedResponse,
    PaginationParams,
    SearchFilter,
    paginate_query,
    search_query,
)

Base = declarative_base()


class Item(Base):
    __tablename__ = "test_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    category = Column(String(100), nullable=False)
    value = Column(Float, default=0.0)
    status = Column(String(50), default="active")
    created_at = Column(DateTime, default=lambda: datetime.now())


@pytest.fixture
def item_engine():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()


@pytest.fixture
def item_session(item_engine):
    session = Session(bind=item_engine)
    yield session
    session.close()


@pytest.fixture
def populated_session(item_session):
    now = datetime.now()
    items = []
    for i in range(25):
        item = Item(
            name=f"Item {i:02d}",
            category="alpha" if i % 2 == 0 else "beta",
            value=float(i * 10),
            status="active" if i < 20 else "archived",
            created_at=now - timedelta(days=24 - i),
        )
        items.append(item)
    item_session.add_all(items)
    item_session.commit()
    return item_session


class TestPaginationParams:
    def test_defaults(self):
        p = PaginationParams()
        assert p.page == 1
        assert p.page_size == 20
        assert p.sort_by is None
        assert p.sort_order == "desc"

    def test_invalid_page_below_1(self):
        with pytest.raises(Exception):
            PaginationParams(page=0)

    def test_invalid_page_size_zero(self):
        with pytest.raises(Exception):
            PaginationParams(page_size=0)

    def test_invalid_page_size_over_100(self):
        with pytest.raises(Exception):
            PaginationParams(page_size=101)

    def test_invalid_sort_order(self):
        with pytest.raises(Exception):
            PaginationParams(sort_order="upward")


class TestPaginateQueryBasic:
    def test_first_page(self, populated_session):
        pagination = PaginationParams(page=1, page_size=10)
        result = paginate_query(
            populated_session.query(Item), pagination, model=Item
        )
        assert len(result["items"]) == 10
        assert result["total"] == 25
        assert result["page"] == 1
        assert result["page_size"] == 10
        assert result["total_pages"] == 3
        assert result["has_next"] is True
        assert result["has_prev"] is False

    def test_last_page(self, populated_session):
        pagination = PaginationParams(page=3, page_size=10)
        result = paginate_query(
            populated_session.query(Item), pagination, model=Item
        )
        assert len(result["items"]) == 5
        assert result["has_next"] is False
        assert result["has_prev"] is True

    def test_single_item_pages(self, populated_session):
        pagination = PaginationParams(page=1, page_size=1)
        result = paginate_query(
            populated_session.query(Item), pagination, model=Item
        )
        assert len(result["items"]) == 1
        assert result["total_pages"] == 25

    def test_page_beyond_total(self, populated_session):
        pagination = PaginationParams(page=100, page_size=10)
        result = paginate_query(
            populated_session.query(Item), pagination, model=Item
        )
        assert len(result["items"]) == 0
        assert result["total"] == 25
        assert result["has_next"] is False


class TestPaginateQuerySorting:
    def test_sort_ascending(self, populated_session):
        pagination = PaginationParams(page=1, page_size=25, sort_by="value", sort_order="asc")
        result = paginate_query(
            populated_session.query(Item), pagination, model=Item
        )
        values = [item.value for item in result["items"]]
        assert values == sorted(values)

    def test_sort_descending(self, populated_session):
        pagination = PaginationParams(page=1, page_size=25, sort_by="value", sort_order="desc")
        result = paginate_query(
            populated_session.query(Item), pagination, model=Item
        )
        values = [item.value for item in result["items"]]
        assert values == sorted(values, reverse=True)

    def test_sort_by_name(self, populated_session):
        pagination = PaginationParams(page=1, page_size=25, sort_by="name", sort_order="asc")
        result = paginate_query(
            populated_session.query(Item), pagination, model=Item
        )
        names = [item.name for item in result["items"]]
        assert names == sorted(names)

    def test_sort_by_nonexistent_field(self, populated_session):
        pagination = PaginationParams(page=1, page_size=10, sort_by="nonexistent", sort_order="asc")
        result = paginate_query(
            populated_session.query(Item), pagination, model=Item
        )
        assert len(result["items"]) == 10


class TestPaginateQueryEmpty:
    def test_empty_result_set(self, item_session):
        pagination = PaginationParams(page=1, page_size=10)
        result = paginate_query(
            item_session.query(Item), pagination, model=Item
        )
        assert result["items"] == []
        assert result["total"] == 0
        assert result["total_pages"] == 1
        assert result["has_next"] is False
        assert result["has_prev"] is False


class TestSearchQueryText:
    def test_text_search_across_fields(self, populated_session):
        sf = SearchFilter(query="Item 05")
        query = populated_session.query(Item)
        query = search_query(query, sf, ["name", "category"], model=Item)
        results = query.all()
        assert len(results) == 1
        assert results[0].name == "Item 05"

    def test_text_search_case_insensitive(self, populated_session):
        sf = SearchFilter(query="ITEM")
        query = populated_session.query(Item)
        query = search_query(query, sf, ["name"], model=Item)
        results = query.all()
        assert len(results) > 0
        for item in results:
            assert "item" in item.name.lower() or "ITEM" in item.name

    def test_text_search_no_match(self, populated_session):
        sf = SearchFilter(query="nonexistent_xyz")
        query = populated_session.query(Item)
        query = search_query(query, sf, ["name"], model=Item)
        assert query.all() == []

    def test_text_search_partial_match(self, populated_session):
        sf = SearchFilter(query="Item 1")
        query = populated_session.query(Item)
        query = search_query(query, sf, ["name"], model=Item)
        results = query.all()
        assert len(results) >= 10


class TestSearchQueryFilters:
    def test_exact_filter(self, populated_session):
        sf = SearchFilter(filters={"category": "alpha"})
        query = populated_session.query(Item)
        query = search_query(query, sf, [], model=Item)
        results = query.all()
        assert all(item.category == "alpha" for item in results)
        assert len(results) == 13

    def test_list_filter(self, populated_session):
        sf = SearchFilter(filters={"category": ["alpha", "beta"]})
        query = populated_session.query(Item)
        query = search_query(query, sf, [], model=Item)
        results = query.all()
        assert len(results) == 25

    def test_none_value_ignored(self, populated_session):
        sf = SearchFilter(filters={"category": None})
        query = populated_session.query(Item)
        query = search_query(query, sf, [], model=Item)
        results = query.all()
        assert len(results) == 25

    def test_combined_text_and_filter(self, populated_session):
        sf = SearchFilter(query="Item 0", filters={"category": "alpha"})
        query = populated_session.query(Item)
        query = search_query(query, sf, ["name"], model=Item)
        results = query.all()
        for item in results:
            assert "Item 0" in item.name
            assert item.category == "alpha"

    def test_nonexistent_filter_field(self, populated_session):
        sf = SearchFilter(filters={"nonexistent": "value"})
        query = populated_session.query(Item)
        query = search_query(query, sf, [], model=Item)
        results = query.all()
        assert len(results) == 25


class TestSearchQueryDateRange:
    def test_date_from(self, populated_session):
        cutoff = datetime.now() - timedelta(days=10)
        sf = SearchFilter(date_from=cutoff)
        query = populated_session.query(Item)
        query = search_query(query, sf, [], model=Item)
        results = query.all()
        assert all(item.created_at >= cutoff for item in results)

    def test_date_to(self, populated_session):
        cutoff = datetime.now() - timedelta(days=10)
        sf = SearchFilter(date_to=cutoff)
        query = populated_session.query(Item)
        query = search_query(query, sf, [], model=Item)
        results = query.all()
        assert all(item.created_at <= cutoff for item in results)

    def test_date_range(self, populated_session):
        now = datetime.now()
        start = now - timedelta(days=15)
        end = now - timedelta(days=5)
        sf = SearchFilter(date_from=start, date_to=end)
        query = populated_session.query(Item)
        query = search_query(query, sf, [], model=Item)
        results = query.all()
        assert len(results) > 0
        for item in results:
            assert start <= item.created_at <= end

    def test_no_date_filter_returns_all(self, populated_session):
        sf = SearchFilter()
        query = populated_session.query(Item)
        query = search_query(query, sf, [], model=Item)
        assert len(query.all()) == 25


class TestPaginatedResponseModel:
    def test_construction(self):
        resp = PaginatedResponse(
            items=[1, 2, 3],
            total=10,
            page=1,
            page_size=3,
            total_pages=4,
            has_next=True,
            has_prev=False,
        )
        assert resp.items == [1, 2, 3]
        assert resp.total == 10
        assert resp.has_next is True
        assert resp.has_prev is False
