from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_migrar_categorias'),
    ]

    operations = [
        # 1. Remover o índice antigo baseado no campo removido
        migrations.AlterUniqueTogether(
            name='interesse',
            unique_together=set(),
        ),

        # 2. Agora sim, remover o campo antigo
        migrations.RemoveField(
            model_name='interesse',
            name='categoria',
        ),

        # 3. Renomear categoria_fk → categoria
        migrations.RenameField(
            model_name='interesse',
            old_name='categoria_fk',
            new_name='categoria',
        ),

        # 4. Recriar o unique_together correto
        migrations.AlterUniqueTogether(
            name='interesse',
            unique_together={('categoria', 'nome')},
        ),

        # 5. Tornar o campo obrigatório
        migrations.AlterField(
            model_name='interesse',
            name='categoria',
            field=models.ForeignKey(
                to='core.Categoria',
                on_delete=models.CASCADE,
                related_name='interesses'
            ),
        ),
    ]
    