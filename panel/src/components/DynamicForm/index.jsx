import { Form } from "antd";
import TextField from "./fields/TextField";
import SecretField from "./fields/SecretField";
import SelectField from "./fields/SelectField";
import BoolField from "./fields/BoolField";
import NumberField from "./fields/NumberField";
import AdminsField from "./fields/AdminsField";

const FIELD_MAP = {
  string: TextField,
  integer: NumberField,
  number: NumberField,
  boolean: BoolField,
};

export default function DynamicForm({ schema, form }) {
  if (!schema?.properties) return null;

  return (
    <Form form={form} layout="vertical">
      {Object.entries(schema.properties).map(([name, fieldSchema]) => {
        const isSecret = fieldSchema.format === "password";
        const isEnum = Array.isArray(fieldSchema.enum);
        const isAdminList = fieldSchema.format === "admins";
        let Component;
        if (isSecret) Component = SecretField;
        else if (isAdminList) Component = AdminsField;
        else if (isEnum) Component = SelectField;
        else Component = FIELD_MAP[fieldSchema.type];
        if (!Component) return null;
        return (
          <Component
            key={name}
            name={name}
            fieldSchema={fieldSchema}
            required={schema.required?.includes(name)}
          />
        );
      })}
    </Form>
  );
}
