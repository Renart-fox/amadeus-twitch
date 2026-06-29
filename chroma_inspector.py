import json
from typing import Optional

import chromadb
import streamlit as st

PAGE_SIZE = 100
DEFAULT_PATH = "./chroma"

st.set_page_config(
    page_title="Chroma Inspector",
    page_icon="🧠",
    layout="wide",
)


# ---------------------------------------------------------
# Chroma
# ---------------------------------------------------------

def connect(path: str):
    return chromadb.PersistentClient(path=path)


def get_collection(client, name: str):
    return client.get_collection(name)


def get_stats(collection):
    count = collection.count()

    sample = collection.peek(limit=1)

    dimension = "Unknown"

    embeddings = sample.get("embeddings")

    if embeddings is not None and len(embeddings) > 0:
        dimension = len(embeddings[0])

    metadata_keys = set()

    meta = collection.get(
        limit=min(100, count),
        include=["metadatas"],
    )["metadatas"]

    for m in meta:
        if m:
            metadata_keys.update(m.keys())

    return {
        "count": count,
        "dimension": dimension,
        "metadata": sorted(metadata_keys),
    }


def get_page(collection, page: int):
    offset = page * PAGE_SIZE

    return collection.get(
        limit=PAGE_SIZE,
        offset=offset,
        include=["documents"],
    )


def get_record(collection, record_id: str):
    result = collection.get(
        ids=[record_id],
        include=[
            "documents",
            "metadatas",
            "embeddings",
        ],
    )

    if not result["ids"]:
        return None

    return {
        "id": result["ids"][0],
        "document": result["documents"][0],
        "metadata": result["metadatas"][0],
        "embedding": result["embeddings"][0],
    }


# ---------------------------------------------------------
# Sidebar
# ---------------------------------------------------------

def render_sidebar():

    st.sidebar.title("🧠 Chroma Inspector")

    path = st.sidebar.text_input(
        "Database",
        DEFAULT_PATH,
    )

    if st.sidebar.button("Refresh"):
        st.session_state.clear()
        st.rerun()

    return path


# ---------------------------------------------------------
# Dashboard
# ---------------------------------------------------------

def render_dashboard(stats):

    c1, c2, c3 = st.columns(3)

    c1.metric("Documents", stats["count"])
    c2.metric("Embedding dimension", stats["dimension"])
    c3.metric("Metadata keys", len(stats["metadata"]))

    with st.expander("Metadata fields"):
        st.write(stats["metadata"])


# ---------------------------------------------------------
# Browser
# ---------------------------------------------------------

def render_browser(collection, stats):

    search = st.text_input("🔍 Keyword search")

    total_pages = max(
        1,
        (stats["count"] + PAGE_SIZE - 1) // PAGE_SIZE,
    )

    page = st.number_input(
        "Page",
        min_value=1,
        max_value=total_pages,
        value=1,
    )

    if search.strip():
        ids, docs = keyword_search(collection, search)
    else:
        page_data = get_page(collection, page - 1)
        ids = page_data["ids"]
        docs = page_data["documents"]

    if not ids:
        st.info("No matching records.")
        return None

    previews = []

    for doc in docs:
        if not doc:
            previews.append("(empty)")
            continue

        preview = doc.replace("\n", " ")

        if len(preview) > 80:
            preview = preview[:80] + "..."

        previews.append(preview)

    options = {
        f"{rid[:8]}... | {preview}": rid
        for rid, preview in zip(ids, previews)
    }

    selected = st.selectbox(
        "Records",
        list(options.keys()),
    )

    return options[selected]


# ---------------------------------------------------------
# Record
# ---------------------------------------------------------

def render_record(record):

    st.subheader("Document")

    document = st.text_area(
        "Document",
        value=record["document"] or "",
        height=250,
    )

    st.subheader("Metadata")

    metadata_text = st.text_area(
        "Metadata (JSON)",
        value=json.dumps(
            record["metadata"] or {},
            indent=2,
        ),
        height=220,
    )

    embedding = record["embedding"]

    st.subheader("Embedding")

    if embedding is None:
        st.warning("No embedding stored.")
    else:

        st.write(f"Dimension: **{len(embedding)}**")

        with st.expander("Show embedding"):

            st.code(
                json.dumps(str(embedding)),
                language="json",
            )

    return document, metadata_text


def update_record(
    collection,
    record_id,
    document,
    metadata,
):
    collection.update(
        ids=[record_id],
        documents=[document],
        metadatas=[metadata],
    )


def delete_record(
    collection,
    record_id,
):
    collection.delete(
        ids=[record_id],
    )


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------

def main():

    st.title("🧠 Chroma Inspector")

    path = render_sidebar()

    client = connect(path)

    collections = client.list_collections()

    if not collections:
        st.error("No collections found.")
        return

    collection_name = st.selectbox(
        "Collection",
        [c.name for c in collections],
    )

    collection = get_collection(
        client,
        collection_name,
    )

    stats = get_stats(collection)

    render_dashboard(stats)

    st.divider()

    left, right = st.columns([1, 2])

    with left:
        selected = render_browser(
            collection,
            stats,
        )

    if selected:

        record = get_record(
            collection,
            selected,
        )

        with right:

            document, metadata_text = render_record(record)

            col1, col2 = st.columns(2)

            #
            # Save
            #

            with col1:

                if st.button(
                    "💾 Save changes",
                    use_container_width=True,
                ):

                    try:

                        metadata = json.loads(metadata_text)

                        update_record(
                            collection,
                            record["id"],
                            document,
                            metadata,
                        )

                        st.success("Record updated.")

                    except json.JSONDecodeError as e:

                        st.error(
                            f"Invalid JSON:\n{e}"
                        )

                    except Exception as e:

                        st.exception(e)

            #
            # Delete
            #

            with col2:

                if st.button(
                    "🗑 Delete",
                    type="primary",
                    use_container_width=True,
                ):

                    delete_record(
                        collection,
                        record["id"],
                    )

                    st.success("Record deleted.")

                    st.rerun()


def keyword_search(
    collection,
    text,
    limit=50,
):

    result = collection.get(
        include=["documents"],
    )

    ids = []
    docs = []

    for rid, doc in zip(
        result["ids"],
        result["documents"],
    ):

        if doc and text.lower() in doc.lower():

            ids.append(rid)
            docs.append(doc)

    return ids, docs


if __name__ == "__main__":
    main()