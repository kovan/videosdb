import { DateTime } from "luxon";

export default function ({ app, $config }, inject) {

    inject("DateTime", DateTime)
}