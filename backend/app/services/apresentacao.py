"""Converte models em objetos JSON do contrato (§3)."""

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.tempo import agora, momento
from app.models import FotoSala, GrupoRecorrencia, Professor, Reserva, Sala
from app.schemas import reservas as sr
from app.schemas import salas as ss
from app.schemas.comum import PessoaResumo, SalaRef
from app.schemas.comum import Semestre as SemestreSaida
from app.schemas.softwares import Software as SoftwareSaida


def pessoa(p: Professor | None) -> PessoaResumo | None:
    return PessoaResumo(id=p.id, nome=p.nome) if p is not None else None


def sala_ref(s: Sala) -> SalaRef:
    return SalaRef(id=s.id, nome=s.nome, tipo=s.tipo)


def fotos_ordenadas(sala: Sala) -> list[FotoSala]:
    return sorted(sala.fotos, key=lambda f: (f.ordem, f.id))


def foto(f: FotoSala) -> ss.Foto:
    return ss.Foto.model_validate(f)


def _equipamentos(sala: Sala) -> list[ss.SalaEquipamento]:
    itens = sorted(sala.equipamentos, key=lambda se: (se.equipamento.nome.lower(), se.equipamento_id))
    return [
        ss.SalaEquipamento(
            equipamento_id=se.equipamento_id,
            nome=se.equipamento.nome,
            quantidade=se.quantidade,
            especificacao=se.especificacao,
        )
        for se in itens
    ]


def _campos_resumo(sala: Sala) -> dict:
    fotos = fotos_ordenadas(sala)
    return {
        "id": sala.id,
        "nome": sala.nome,
        "tipo": sala.tipo,
        "tipo_rotulo": sala.tipo_rotulo,
        "capacidade": sala.capacidade,
        "localizacao": sala.localizacao,
        "ativo": sala.ativo,
        "foto_capa_url": fotos[0].url if fotos else None,
        "equipamentos": _equipamentos(sala),
    }


def sala_resumo(sala: Sala) -> ss.SalaResumo:
    return ss.SalaResumo(**_campos_resumo(sala))


def sala_detalhe(sala: Sala) -> ss.SalaDetalhe:
    softwares = sorted(sala.softwares, key=lambda s: (s.nome.lower(), s.versao or "", s.id))
    return ss.SalaDetalhe(
        **_campos_resumo(sala),
        descricao=sala.descricao,
        fotos=[foto(f) for f in fotos_ordenadas(sala)],
        softwares=[SoftwareSaida.model_validate(s) for s in softwares],
        criado_em=sala.criado_em,
        atualizado_em=sala.atualizado_em,
    )


def pode_cancelar(r: Reserva, usuario: Professor | None, referencia: datetime | None = None) -> bool:
    if usuario is None or r.status != "ativa":
        return False
    if usuario.eh_admin:
        return True
    return r.professor_id == usuario.id and (referencia or agora()) < momento(r.data, r.inicio)


def reserva(r: Reserva, usuario: Professor | None, referencia: datetime | None = None) -> sr.Reserva:
    return sr.Reserva(
        id=r.id,
        sala=sala_ref(r.sala),
        professor=pessoa(r.professor),
        data=r.data,
        inicio=r.inicio,
        fim=r.fim,
        horario_inicio_id=r.horario_inicio_id,
        horario_fim_id=r.horario_fim_id,
        quantidade_aulas=r.quantidade_aulas,
        status=r.status,
        observacao=r.observacao,
        grupo_recorrencia_id=r.grupo_recorrencia_id,
        criado_em=r.criado_em,
        cancelada_em=r.cancelada_em,
        cancelada_por=pessoa(r.cancelada_por),
        motivo_cancelamento=r.motivo_cancelamento,
        pode_cancelar=pode_cancelar(r, usuario, referencia),
    )


def reservas(lista: list[Reserva], usuario: Professor | None) -> list[sr.Reserva]:
    ref = agora()
    return [reserva(r, usuario, ref) for r in lista]


def conflito(r: Reserva) -> sr.Conflito:
    return sr.Conflito(
        data=r.data, inicio=r.inicio, fim=r.fim, reserva_id=r.id, sala_id=r.sala_id, professor=pessoa(r.professor)
    )


def grupo(db: Session, g: GrupoRecorrencia) -> sr.GrupoRecorrencia:
    total, ativas = db.execute(
        select(func.count(Reserva.id), func.count(Reserva.id).filter(Reserva.status == "ativa")).where(
            Reserva.grupo_recorrencia_id == g.id
        )
    ).one()
    return sr.GrupoRecorrencia(
        id=g.id,
        sala=sala_ref(g.sala),
        professor=pessoa(g.professor),
        semestre=SemestreSaida.model_validate(g.semestre),
        dia_semana=g.dia_semana,
        inicio=g.inicio,
        fim=g.fim,
        criado_em=g.criado_em,
        total_ocorrencias=total,
        ocorrencias_ativas=ativas,
    )
