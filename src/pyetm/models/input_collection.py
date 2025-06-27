import pandas as pd

from pydantic import BaseModel
from .input import Input


class InputCollection(BaseModel):
    inputs: list["Input"]

    def __len__(self):
        return len(self.inputs)

    def __iter__(self):
        yield from iter(self.inputs)

    def keys(self):
        return [input.key for input in self.inputs]

    def to_dataframe(self) -> pd.DataFrame:
        ''' Used for export '''
        columns = ['unit', 'value', 'default']#, 'min', 'max']

        # Should come from input itself once we know what we want ;)
        return pd.DataFrame.from_dict(
            {input.key: [input.unit, input.user, input.default] for input in self.inputs},
            orient='index',
            columns=columns
        )

    @classmethod
    def from_json(cls, data):
        return cls(inputs=[Input.from_json(item) for item in data.items()])
