from sqlalchemy.sql import functions
from sqlalchemy.sql.selectable import FromClause
from sqlalchemy.sql.elements import ColumnClause
from sqlalchemy.ext.compiler import compiles

# https://bitbucket.org/zzzeek/sqlalchemy/issues/3566/figure-out-how-to-support-all-of-pgs#comment-22842678


class FunctionColumn(ColumnClause):
    def __init__(self, function, name, type_=None):
        self.function = self.table = function
        self.name = self.key = name
        self.type_ = type_
        self.is_literal = False

    @property
    def _from_objects(self):
        return []

    def _make_proxy(self, selectable, name=None, attach=True,
                    name_is_truncatable=False, **kw):
        co = ColumnClause(self.name, self.type)
        co._proxies = [self]
        if selectable._is_clone_of is not None:
            co._is_clone_of = \
                selectable._is_clone_of.columns.get(co.key)

        if attach:
            selectable._columns[co.key] = co
        return co


@compiles(FunctionColumn)
def _compile_function_column(element, compiler, **kw):
    return "(%s).%s" % (
        compiler.process(element.function, **kw),
        compiler.preparer.quote(element.name)
    )


class ColumnFunction(functions.FunctionElement):
    __visit_name__ = 'function'

    @property
    def columns(self):
        return FromClause.columns.fget(self)

    def _populate_column_collection(self):
        for name in self.column_names:
            self._columns[name] = FunctionColumn(self, name)


class extract_feature(ColumnFunction):
    name = 'jsonb_array_elements_text'
    column_names = ['feature']


class extract_other_feature(ColumnFunction):
    name = 'jsonb_array_elements_text'
    column_names = ['other_feature']


class jsonb_object_keys(ColumnFunction):
    name = 'jsonb_object_keys'
    #column_names = ['value']
