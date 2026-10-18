"""Manage the customers' stores from the Hangar terminal:

  python manage.py loja criar "Padaria da Ana" padaria.example.com
  python manage.py loja listar
  python manage.py loja desativar padaria.example.com
"""

from django.core.management.base import BaseCommand, CommandError

from lab.models import Store


class Command(BaseCommand):
    help = "Cria, lista e desativa lojas (cada uma no seu domínio)."

    def add_arguments(self, parser):
        parser.add_argument("acao", choices=["criar", "listar", "desativar", "ativar"])
        parser.add_argument("valores", nargs="*")

    def handle(self, *_, acao, valores, **__):
        args = valores
        if acao == "listar":
            for s in Store.objects.order_by("id"):
                self.stdout.write(f"{'ativa  ' if s.active else 'inativa'}  {s.domain}  ({s.name})")
            return
        if acao == "criar":
            if len(args) != 2:
                raise CommandError('uso: loja criar "Nome" dominio')
            s = Store.objects.create(name=args[0], domain=args[1].strip().lower())
            self.stdout.write(f"loja criada: {s.domain}")
            return
        if len(args) != 1:
            raise CommandError(f"uso: loja {acao} dominio")
        n = Store.objects.filter(domain=args[0].strip().lower()).update(active=(acao == "ativar"))
        self.stdout.write(f"{n} loja(s) {'ativada' if acao == 'ativar' else 'desativada'}(s)")
