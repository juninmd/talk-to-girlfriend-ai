import pytest
from sqlmodel import Session, SQLModel, create_engine, select, or_
from backend.database import Fact


@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def test_fact_personalization(session):
    # Setup
    chat_id_private = 1001
    chat_id_group = 1002
    sender_id = 999

    # Add a fact learned in Private Chat about Sender
    fact = Fact(
        chat_id=chat_id_private,
        sender_id=sender_id,
        entity_name="User Name",
        value="Jules",
        category="personal",
    )
    session.add(fact)
    session.commit()

    # Verify we can find it when querying for the GROUP chat context + Sender
    query = select(Fact).where(or_(Fact.chat_id == chat_id_group, Fact.sender_id == sender_id))
    results = session.exec(query).all()

    assert len(results) == 1
    assert results[0].value == "Jules"
    assert results[0].sender_id == sender_id


def test_fact_isolation(session):
    # Setup
    chat_id_1 = 1001
    chat_id_2 = 1002
    sender_id = 999
    other_sender = 888

    # Fact for chat 1, different sender
    fact = Fact(
        chat_id=chat_id_1,
        sender_id=other_sender,
        entity_name="Topic",
        value="Python",
        category="general",
    )
    session.add(fact)
    session.commit()

    # Query for Chat 2 and Sender 999
    query = select(Fact).where(or_(Fact.chat_id == chat_id_2, Fact.sender_id == sender_id))
    results = session.exec(query).all()

    # Should not find it because chat_id doesn't match and sender_id doesn't match
    assert len(results) == 0
